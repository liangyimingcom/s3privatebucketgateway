# API文档

## 🎯 概述

S3私有桶网关代理提供内容服务和管理API，用于管理代理服务和缓存。

## 🌐 内容API

### 基础URL
```
http://你的实例IP/
```

### 通用内容访问

#### `GET /{路径}`
从S3提供内容，具备智能子目录重定向功能。

**参数:**
- `路径` (可选): 任意路径，支持嵌套目录
- `refresh` (查询参数，可选): 设置为 `1` 强制刷新缓存

**示例:**
```bash
# 根目录访问
GET /
# 返回: S3根目录的index.html

# 直接文件访问
GET /文件.html
# 返回: 文件存在则返回文件内容

# 目录访问
GET /website1/
# 返回: website1/index.html

# 子目录重定向 (404 → index.html)
GET /website1/缺失页面
# 返回: website1/index.html 带重定向头

# 深层嵌套重定向
GET /app1/非常/深层/嵌套/路径
# 返回: app1/index.html 带重定向头

# 根目录回退
GET /不存在目录/页面
# 返回: 根目录index.html 带回退头

# 强制刷新
GET /website1/?refresh=1
# 返回: 从S3获取的新内容，绕过缓存
```

**响应头:**

| 响应头 | 描述 | 示例 |
|--------|------|------|
| `X-S3-Key` | 实际提供的S3对象键 | `website1/index.html` |
| `X-Direct-Hit` | 直接文件访问 (无重定向) | `true` |
| `X-Directory-Index` | 目录索引访问 | `true` |
| `X-Subdirectory-Redirect` | 子目录404重定向 | `true` |
| `X-Root-Fallback` | 根目录回退 | `true` |
| `X-Redirected-From` | 原始请求路径 | `/website1/缺失` |
| `X-Redirected-To` | 最终服务路径 | `/website1/index.html` |
| `X-Cache-Status` | 缓存状态 | `HIT`, `MISS`, `REFRESHED` |

**响应码:**
- `200 OK`: 内容成功提供
- `404 Not Found`: 未找到内容 (所有重定向尝试后)
- `500 Internal Server Error`: S3或应用错误

## 🔧 管理API

### 健康检查

#### `GET /health`
服务健康检查端点。

**响应:**
```
OK
```

**响应头:**
```
Content-Type: text/plain
```

**示例:**
```bash
curl http://你的IP/health
# 响应: OK
```

### 缓存管理

#### `GET /admin/cache/status`
获取当前缓存状态和统计信息。

**响应:**
```json
{
    "cache_dir": "/var/cache/s3-proxy",
    "cache_ttl": 60,
    "total_files": 5,
    "bucket": "s3-gateway-123456789-us-east-1",
    "region": "us-east-1",
    "files": [
        {
            "file": "index.html",
            "size": 1024,
            "age_seconds": 45,
            "valid": true
        },
        {
            "file": "website1_index.html",
            "size": 2048,
            "age_seconds": 120,
            "valid": false
        }
    ]
}
```

**字段说明:**
- `cache_dir`: 缓存目录路径
- `cache_ttl`: 缓存TTL秒数
- `total_files`: 缓存文件数量
- `bucket`: S3桶名称
- `region`: AWS区域
- `files[]`: 缓存文件数组
  - `file`: 缓存文件名
  - `size`: 文件大小(字节)
  - `age_seconds`: 上次更新后的时间
  - `valid`: 缓存是否仍有效 (age < TTL)

**示例:**
```bash
curl http://你的IP/admin/cache/status | jq
```

#### `POST /admin/cache/clear`
#### `GET /admin/cache/clear`
清除所有缓存文件。

**响应:**
```json
{
    "status": "success",
    "message": "已清除5个缓存文件",
    "cleared_count": 5
}
```

**错误响应:**
```json
{
    "status": "error",
    "message": "权限被拒绝"
}
```

**示例:**
```bash
# POST方法
curl -X POST http://你的IP/admin/cache/clear

# GET方法 (便于使用)
curl http://你的IP/admin/cache/clear
```

## 🔍 响应示例

### 直接文件访问
```bash
curl -I http://你的IP/index.html
```
```http
HTTP/1.1 200 OK
Server: nginx/1.28.0
Content-Type: text/html
Content-Length: 1024
X-S3-Key: index.html
X-Direct-Hit: true
```

### 目录索引访问
```bash
curl -I http://你的IP/website1/
```
```http
HTTP/1.1 200 OK
Server: nginx/1.28.0
Content-Type: text/html
Content-Length: 2048
X-S3-Key: website1/index.html
X-Directory-Index: true
```

### 子目录404重定向
```bash
curl -I http://你的IP/website1/缺失页面
```
```http
HTTP/1.1 200 OK
Server: nginx/1.28.0
Content-Type: text/html
Content-Length: 2048
X-S3-Key: website1/index.html
X-Redirected-From: /website1/缺失页面
X-Redirected-To: /website1/index.html
X-Subdirectory-Redirect: true
```

### 根目录回退
```bash
curl -I http://你的IP/不存在目录/页面
```
```http
HTTP/1.1 200 OK
Server: nginx/1.28.0
Content-Type: text/html
Content-Length: 1024
X-S3-Key: index.html
X-Redirected-From: /不存在目录/页面
X-Redirected-To: /index.html
X-Root-Fallback: true
```

### 强制刷新
```bash
curl -I http://你的IP/website1/?refresh=1
```
```http
HTTP/1.1 200 OK
Server: nginx/1.28.0
Content-Type: text/html
Content-Length: 2048
X-S3-Key: website1/index.html
X-Directory-Index: true
X-Cache-Status: REFRESHED
```

## 🚀 使用模式

### 内容管理工作流

1. **上传内容到S3:**
   ```bash
   aws s3 cp 新页面.html s3://你的桶名/website1/
   ```

2. **清除缓存以立即更新:**
   ```bash
   curl http://你的IP/admin/cache/clear
   ```

3. **验证内容:**
   ```bash
   curl http://你的IP/website1/新页面.html
   ```

### 监控和调试

1. **检查服务健康:**
   ```bash
   curl http://你的IP/health
   ```

2. **监控缓存性能:**
   ```bash
   curl http://你的IP/admin/cache/status | jq '.files[] | select(.valid == false)'
   ```

3. **调试重定向行为:**
   ```bash
   curl -I http://你的IP/任意/路径/这里
   # 检查 X-Redirected-* 响应头
   ```

### 性能测试

```bash
# 测试并发请求
ab -n 1000 -c 10 http://你的IP/

# 测试重定向性能
ab -n 100 -c 5 http://你的IP/website1/测试404

# 测试缓存命中率
for i in {1..10}; do
  curl -I http://你的IP/website1/ 2>/dev/null | grep X-Cache-Status || echo "MISS"
done
```

## 🔒 安全考虑

### 访问控制
- 管理端点 (`/admin/*`) 在生产环境中应受限制
- 考虑为管理访问添加IP白名单
- 在生产环境中使用HTTPS

### 速率限制
- 无内置速率限制 (依赖Nginx/上游)
- 考虑为管理端点添加速率限制
- 监控滥用模式

### 输入验证
- 内置路径遍历保护
- 安全处理特殊字符
- 不直接执行用户输入

## 🐛 错误处理

### 常见错误响应

#### 404 Not Found
```json
{
    "error": "Not Found",
    "message": "服务器上未找到请求的URL。"
}
```

#### 500 Internal Server Error
```json
{
    "error": "Internal Server Error",
    "message": "S3访问错误或应用程序故障"
}
```

### 调试响应头

所有响应都包含调试信息:
- 请求路径处理
- S3键解析
- 重定向决策逻辑
- 缓存状态

## 📊 性能指标

### 典型响应时间
- **缓存命中**: < 50ms
- **缓存未命中**: < 500ms
- **S3获取**: 100-300ms
- **重定向处理**: < 10ms

### 缓存效率
- **命中率**: 预热后 > 90%
- **TTL**: 60秒 (可配置)
- **存储**: 本地文件系统

## 🔄 API版本控制

当前API版本: `v1.0`

未来版本将保持向后兼容:
- 内容服务端点
- 响应头格式
- 基础管理端点

重大变更仅在主版本中引入。

---

**下一步**: 查看 [故障排除.md](故障排除.md) 了解常见问题和解决方案。
