#!/usr/bin/env python3

import boto3
import os
import glob
from flask import Flask, request, Response, abort, jsonify
from botocore.exceptions import ClientError
import mimetypes
import time

app = Flask(__name__)

# S3配置 - 将在部署时替换
BUCKET_NAME = 'BUCKET_PLACEHOLDER'
REGION = 'REGION_PLACEHOLDER'

# 创建S3客户端
s3_client = boto3.client('s3', region_name=REGION)

# 缓存配置
CACHE_DIR = '/var/cache/s3-proxy'
CACHE_TTL = 60  # 1分钟

def ensure_cache_dir():
    """确保缓存目录存在"""
    os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(key):
    """获取缓存文件路径"""
    return os.path.join(CACHE_DIR, key.replace('/', '_'))

def is_cache_valid(cache_path):
    """检查缓存是否有效"""
    if not os.path.exists(cache_path):
        return False
    cache_age = time.time() - os.path.getmtime(cache_path)
    return cache_age < CACHE_TTL

def get_s3_object(key):
    """从S3获取对象"""
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        return response['Body'].read(), response.get('ContentType', 'application/octet-stream')
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None, None
        raise

def serve_from_cache_or_s3(key, force_refresh=False):
    """从缓存或S3提供内容"""
    ensure_cache_dir()
    cache_path = get_cache_path(key)
    
    # 检查缓存（除非强制刷新）
    if not force_refresh and is_cache_valid(cache_path):
        with open(cache_path, 'rb') as f:
            content = f.read()
        content_type = mimetypes.guess_type(key)[0] or 'application/octet-stream'
        return content, content_type
    
    # 从S3获取
    content, content_type = get_s3_object(key)
    if content is None:
        return None, None
    
    # 保存到缓存
    try:
        with open(cache_path, 'wb') as f:
            f.write(content)
    except Exception as e:
        print(f"缓存写入错误: {e}")
    
    return content, content_type

def get_subdirectory_from_path(path):
    """从路径中提取子目录名称 - 通用函数，支持任意子目录"""
    if not path or path == '/':
        return None
    
    # 移除开头和结尾的斜杠，然后分割
    clean_path = path.strip('/')
    if not clean_path:
        return None
    
    parts = clean_path.split('/')
    return parts[0] if parts else None

def try_subdirectory_redirect(original_path):
    """尝试子目录级重定向 - 通用逻辑，无硬编码子目录"""
    subdirectory = get_subdirectory_from_path(original_path)
    
    if not subdirectory:
        return None, None, None
    
    # 尝试子目录的index.html
    redirect_key = f"{subdirectory}/index.html"
    content, content_type = serve_from_cache_or_s3(redirect_key)
    
    if content is not None:
        return content, content_type, redirect_key
    
    return None, None, None

def try_root_fallback():
    """尝试回退到根目录index.html"""
    content, content_type = serve_from_cache_or_s3('index.html')
    if content is not None:
        return content, content_type, 'index.html'
    return None, None, None

@app.route('/health')
def health():
    """健康检查端点"""
    return 'OK', 200, {'Content-Type': 'text/plain'}

@app.route('/admin/cache/clear', methods=['POST', 'GET'])
def clear_cache():
    """清除所有缓存"""
    try:
        cache_files = glob.glob(os.path.join(CACHE_DIR, '*'))
        cleared_count = 0
        for cache_file in cache_files:
            if os.path.isfile(cache_file):
                os.remove(cache_file)
                cleared_count += 1
        
        return jsonify({
            'status': 'success',
            'message': f'已清除 {cleared_count} 个缓存文件',
            'cleared_count': cleared_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/admin/cache/status')
def cache_status():
    """查看缓存状态"""
    try:
        cache_files = glob.glob(os.path.join(CACHE_DIR, '*'))
        cache_info = []
        
        for cache_file in cache_files:
            if os.path.isfile(cache_file):
                stat = os.stat(cache_file)
                age = time.time() - stat.st_mtime
                cache_info.append({
                    'file': os.path.basename(cache_file),
                    'size': stat.st_size,
                    'age_seconds': int(age),
                    'valid': age < CACHE_TTL
                })
        
        return jsonify({
            'cache_dir': CACHE_DIR,
            'cache_ttl': CACHE_TTL,
            'total_files': len(cache_info),
            'files': cache_info,
            'bucket': BUCKET_NAME,
            'region': REGION
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy_s3(path):
    """
    S3代理主函数 - 实现通用子目录404重定向
    
    重定向逻辑:
    1. 直接文件访问 - 文件存在则直接返回
    2. 目录索引访问 - 自动添加 /index.html 后缀
    3. 子目录404重定向 - 提取子目录名，重定向到 [subdirectory]/index.html
    4. 根目录回退 - 子目录不存在时回退到根 index.html
    5. 最终404 - 所有尝试失败返回404错误
    
    特点: 通用设计，无硬编码子目录，支持任意未来子目录
    """
    # 检查是否强制刷新
    force_refresh = request.args.get('refresh') == '1'
    original_path = '/' + path if path else '/'
    
    # 清理路径
    if not path or path == '/':
        path = 'index.html'
    
    # 尝试直接获取文件
    content, content_type = serve_from_cache_or_s3(path, force_refresh)
    
    if content is not None:
        response = Response(content, content_type=content_type)
        response.headers['X-S3-Key'] = path
        response.headers['X-Direct-Hit'] = 'true'
        if force_refresh:
            response.headers['X-Cache-Status'] = 'REFRESHED'
        return response
    
    # 如果直接访问失败，尝试添加index.html（用于目录访问）
    if not path.endswith('/') and not path.endswith('.html'):
        # 尝试 path/index.html
        directory_index = f"{path}/index.html"
        content, content_type = serve_from_cache_or_s3(directory_index, force_refresh)
        if content is not None:
            response = Response(content, content_type=content_type)
            response.headers['X-S3-Key'] = directory_index
            response.headers['X-Directory-Index'] = 'true'
            if force_refresh:
                response.headers['X-Cache-Status'] = 'REFRESHED'
            return response
    
    # 如果以/结尾，尝试添加index.html
    if path.endswith('/'):
        directory_index = f"{path}index.html"
        content, content_type = serve_from_cache_or_s3(directory_index, force_refresh)
        if content is not None:
            response = Response(content, content_type=content_type)
            response.headers['X-S3-Key'] = directory_index
            response.headers['X-Directory-Index'] = 'true'
            if force_refresh:
                response.headers['X-Cache-Status'] = 'REFRESHED'
            return response
    
    # 子目录级404重定向 - 通用逻辑，支持任意子目录
    content, content_type, redirect_key = try_subdirectory_redirect(original_path)
    if content is not None:
        response = Response(content, content_type=content_type)
        response.headers['X-Redirected-From'] = original_path
        response.headers['X-Redirected-To'] = '/' + redirect_key
        response.headers['X-Subdirectory-Redirect'] = 'true'
        response.headers['X-S3-Key'] = redirect_key
        if force_refresh:
            response.headers['X-Cache-Status'] = 'REFRESHED'
        return response
    
    # 回退到根目录
    content, content_type, fallback_key = try_root_fallback()
    if content is not None:
        response = Response(content, content_type=content_type)
        response.headers['X-Redirected-From'] = original_path
        response.headers['X-Redirected-To'] = '/' + fallback_key
        response.headers['X-Root-Fallback'] = 'true'
        response.headers['X-S3-Key'] = fallback_key
        if force_refresh:
            response.headers['X-Cache-Status'] = 'REFRESHED'
        return response
    
    # 最终404
    abort(404)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=False)
