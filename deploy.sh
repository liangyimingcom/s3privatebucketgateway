#!/bin/bash

# S3私有桶网关代理 - 一键部署脚本
# 使用方法: ./deploy.sh [堆栈名称] [密钥对名称] [区域]

set -e

# 默认值
STACK_NAME=${1:-s3-private-gateway-proxy}
KEY_PAIR_NAME=${2}
REGION=${3:-us-east-1}
PROJECT_NAME="s3-gateway"

# 输出颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

echo -e "${BLUE}🚀 S3私有桶网关代理 - 一键部署${NC}"
echo "=================================================="

# 验证输入参数
if [ -z "$KEY_PAIR_NAME" ]; then
    echo -e "${RED}❌ 错误: 需要提供密钥对名称${NC}"
    echo "使用方法: $0 [堆栈名称] <密钥对名称> [区域]"
    echo "示例: $0 我的代理 我的密钥对 us-west-2"
    exit 1
fi

echo -e "${YELLOW}📋 部署配置:${NC}"
echo "  堆栈名称: $STACK_NAME"
echo "  密钥对: $KEY_PAIR_NAME"
echo "  区域: $REGION"
echo "  项目: $PROJECT_NAME"
echo ""

# 检查AWS CLI配置
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo -e "${RED}❌ 错误: AWS CLI未配置或无有效凭证${NC}"
    echo "请先运行 'aws configure'"
    exit 1
fi

# 检查密钥对是否存在
if ! aws ec2 describe-key-pairs --key-names "$KEY_PAIR_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo -e "${RED}❌ 错误: 在区域 '$REGION' 中未找到密钥对 '$KEY_PAIR_NAME'${NC}"
    echo "请先创建密钥对或使用现有的密钥对"
    exit 1
fi

echo -e "${YELLOW}🔍 验证CloudFormation模板...${NC}"
aws cloudformation validate-template \
    --template-body file://infrastructure/cloudformation-template.yaml \
    --region "$REGION" >/dev/null

echo -e "${GREEN}✅ 模板验证成功${NC}"

echo -e "${YELLOW}🚀 部署CloudFormation堆栈...${NC}"
aws cloudformation deploy \
    --template-file infrastructure/cloudformation-template.yaml \
    --stack-name "$STACK_NAME" \
    --parameter-overrides \
        KeyPairName="$KEY_PAIR_NAME" \
        ProjectName="$PROJECT_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 堆栈部署成功!${NC}"
    
    # 获取输出信息
    echo -e "${YELLOW}📊 获取部署信息...${NC}"
    
    BUCKET_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
        --output text)
    
    PUBLIC_IP=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
        --output text)
    
    INSTANCE_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
        --output text)
    
    echo ""
    echo -e "${GREEN}🎉 部署完成!${NC}"
    echo "=========================="
    echo -e "${BLUE}📦 S3桶名称:${NC} $BUCKET_NAME"
    echo -e "${BLUE}🖥️  实例ID:${NC} $INSTANCE_ID"
    echo -e "${BLUE}🌐 公网IP:${NC} $PUBLIC_IP"
    echo -e "${BLUE}🔗 网站URL:${NC} http://$PUBLIC_IP"
    echo -e "${BLUE}❤️  健康检查:${NC} http://$PUBLIC_IP/health"
    echo ""
    echo -e "${YELLOW}⏳ 注意: 请等待2-3分钟让实例完全初始化${NC}"
    echo ""
    echo -e "${BLUE}🧪 测试命令:${NC}"
    echo "  curl http://$PUBLIC_IP/health"
    echo "  curl http://$PUBLIC_IP/"
    echo "  curl http://$PUBLIC_IP/website1/"
    echo "  curl http://$PUBLIC_IP/app1/缺失页面"
    echo ""
    echo -e "${BLUE}🔧 缓存管理:${NC}"
    echo "  curl http://$PUBLIC_IP/admin/cache/status"
    echo "  curl http://$PUBLIC_IP/admin/cache/clear"
    echo ""
    echo -e "${BLUE}🗑️  删除堆栈:${NC}"
    echo "  aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
    
else
    echo -e "${RED}❌ 堆栈部署失败!${NC}"
    exit 1
fi
