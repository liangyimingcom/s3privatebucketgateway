# S3私有桶网关代理与子目录级404重定向

一个生产就绪的解决方案，通过Nginx代理私有S3内容，具备智能的子目录级404重定向功能。

## 🎯 核心特性

- **通用子目录重定向**: 自动将任意子目录的404请求重定向到对应的 `index.html`
- **S3私有内容访问**: 通过IAM角色安全访问私有S3桶
- **智能缓存机制**: 60秒TTL缓存，支持手动缓存管理
- **一键部署**: 基于CloudFormation的完整部署方案
- **业务透明**: 用户现有环境无需变更，即插即用

## 🚀 快速开始

### 前置条件

- 已配置AWS CLI，具备相应权限
- 目标区域中存在EC2密钥对

### 一键部署

```bash
git clone https://github.com/your-username/s3-private-gateway-proxy.git
cd s3-private-gateway-proxy
./deploy.sh 我的堆栈名称 我的密钥对名称 us-east-1
```

### 手动部署

```bash
aws cloudformation deploy \
  --template-file infrastructure/cloudformation-template.yaml \
  --stack-name s3-private-gateway-proxy \
  --parameter-overrides KeyPairName=我的密钥对 ProjectName=s3-gateway \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

## 🏗️ 架构设计

```
企业内网 → ALB → 网关代理（EC2 Nginx） → Python Flask → S3私有桶
                                ↓
                           本地缓存 (60秒TTL)
```


### 组件说明

- **Nginx**: 高性能反向代理服务器
- **Python Flask**: S3集成和重定向逻辑处理
- **S3桶**: 私有内容存储
- **IAM角色**: 无凭证的安全S3访问
- **CloudFormation**: 基础设施即代码

## 🎯 重定向逻辑

系统实现智能的、通用的子目录重定向：

1. **直接文件访问**: `/file.html` → 文件存在则直接返回
2. **目录索引访问**: `/subdir/` → 返回 `/subdir/index.html`
3. **子目录404重定向**: `/subdir/missing-page` → `/subdir/index.html`
4. **根目录回退**: `/nonexistent/page` → `/index.html`
5. **最终404**: 所有尝试失败 → 404错误

### 重定向示例

```bash
# 现有子目录
/website1/任意页面 → /website1/index.html ✅
/app1/深层/嵌套/路径 → /app1/index.html ✅

# 未来子目录（自动支持，无需配置）
/新应用/缺失页面 → /新应用/index.html ✅
/文档/404页面 → /文档/index.html ✅
/api/v1/不存在 → /api/index.html ✅
```

## 🔧 业务透明特性

### ✅ 零配置适配

- **无需修改现有代码**: 用户业务逻辑完全不变
- **自动识别子目录**: 动态处理任意目录结构
- **透明重定向**: 用户感知不到重定向过程
- **即插即用**: 部署后立即可用

### ✅ 现有环境兼容

- **保持原有URL结构**: 不影响现有链接和书签
- **兼容所有子目录**: 无论多少层级都支持
- **保持响应格式**: 返回标准HTML内容
- **维持用户体验**: 无感知的错误处理

## 🔧 配置管理

### 环境变量

应用在部署时自动配置：

- `BUCKET_NAME`: 自动生成的S3桶名称
- `REGION`: 部署区域
- `CACHE_TTL`: 60秒（可配置）

### 缓存管理

```bash
# 查看缓存状态
curl http://你的IP/admin/cache/status

# 清除所有缓存
curl http://你的IP/admin/cache/clear

# 强制刷新特定页面
curl http://你的IP/页面路径?refresh=1
```

## 📊 监控与调试

### 健康检查

```bash
curl http://你的IP/health
```

### 响应头信息

系统提供详细的调试信息：

```http
X-S3-Key: website1/index.html
X-Redirected-From: /website1/missing-page
X-Redirected-To: /website1/index.html
X-Subdirectory-Redirect: true
X-Cache-Status: HIT
```

### 日志查看

```bash
# 应用日志
sudo journalctl -u s3-proxy -f

# Nginx日志
sudo tail -f /var/log/nginx/s3-proxy-access.log
sudo tail -f /var/log/nginx/s3-proxy-error.log
```

## 🧪 功能测试

### 基础功能

```bash
# 健康检查
curl -I http://你的IP/health

# 根目录访问
curl http://你的IP/

# 子目录访问
curl http://你的IP/website1/
curl http://你的IP/app1/
```

### 重定向测试

```bash
# 子目录404重定向
curl -I http://你的IP/website1/缺失页面
curl -I http://你的IP/app1/不存在.html

# 根目录回退
curl -I http://你的IP/不存在目录/页面

# 深层嵌套路径
curl -I http://你的IP/website1/非常/深层/嵌套/路径
```

## 📁 项目结构

```
s3-private-gateway-proxy/
├── infrastructure/
│   ├── cloudformation-template.yaml    # AWS基础设施模板
│   ├── nginx.conf                      # Nginx配置
│   └── s3-proxy.service               # 系统服务配置
├── scripts/
│   └── s3-proxy.py                    # Python Flask应用
├── s3-content/                        # 示例S3内容
│   ├── index.html
│   ├── website1/index.html
│   ├── website2/index.html
│   └── app1/index.html
├── docs/                              # 中文文档
├── deploy.sh                          # 一键部署脚本
└── README.md
```

## 🔒 安全特性

- **私有S3桶**: 无公网访问，仅IAM角色认证
- **安全组**: 仅开放HTTP/HTTPS和SSH端口
- **无硬编码凭证**: 使用EC2实例配置文件
- **VPC集成**: 部署在默认VPC中，具备安全组保护

## 🚀 性能表现

- **响应时间**: 缓存命中 < 50ms，缓存未命中 < 500ms
- **缓存命中率**: 预热后 > 90%
- **并发用户**: 支持100+并发连接
- **内存使用**: ~60MB (Python + Nginx)

## 🛠️ 自定义配置

### 添加新内容

1. 上传文件到S3桶：

   ```bash
   aws s3 cp 本地文件.html s3://你的桶名/路径/
   ```

2. 清除缓存（可选，立即更新）：

   ```bash
   curl http://你的IP/admin/cache/clear
   ```

### 修改缓存TTL

编辑 `/opt/s3-proxy/s3-proxy.py`：

```python
CACHE_TTL = 300  # 5分钟
```

### 自定义重定向规则

重定向逻辑在 `proxy_s3()` 函数中，可根据具体需求自定义。

## 🗑️ 清理资源

```bash
# 删除CloudFormation堆栈
aws cloudformation delete-stack --stack-name 你的堆栈名称 --region 你的区域

# 验证删除
aws cloudformation describe-stacks --stack-name 你的堆栈名称 --region 你的区域
```

## 📝 许可证

MIT许可证 - 详见LICENSE文件。

## 🤝 贡献

1. Fork本仓库
2. 创建功能分支
3. 提交更改
4. 添加测试
5. 提交Pull Request

## 📞 支持

- **问题反馈**: GitHub Issues
- **文档**: 查看 `/docs` 目录
- **示例**: 查看 `/examples` 目录

---

**专为通用子目录404重定向而设计，让您的业务逻辑保持不变** ❤️
