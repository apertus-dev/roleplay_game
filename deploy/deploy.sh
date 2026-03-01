#!/bin/bash
set -e

# ============================================================
# 《守门人的突围》一键部署脚本
# 架构：CloudFront → ALB (仅CF可访问) → ECS Fargate
# ============================================================

REGION="ap-northeast-1"
ACCOUNT_ID="722977099337"
CLUSTER="jpn-start-ecs-cluster"
VPC_ID="vpc-0a0276401252ad557"
SUBNETS="subnet-0624f33aa92cdb358,subnet-05fe69b6f7cc34a91,subnet-01e941ac776ef1073"
SUBNET_LIST="subnet-0624f33aa92cdb358 subnet-05fe69b6f7cc34a91 subnet-01e941ac776ef1073"
ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/roleplay-game"
EXECUTION_ROLE="arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole"
CF_SECRET=$(openssl rand -hex 16)
APP_SECRET=$(openssl rand -hex 24)
# CloudFront 托管前缀列表 (ap-northeast-1)
CF_PREFIX_LIST="pl-58a04531"

echo "============================================"
echo "  开始部署《守门人的突围》"
echo "  CF Secret: ${CF_SECRET}"
echo "============================================"

# ------ Step 1: 构建推送镜像 ------
echo ""
echo ">>> Step 1/7: 构建并推送 Docker 镜像..."

aws ecr get-login-password --region ${REGION} | \
  docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

docker build --platform linux/amd64 -t roleplay-game .
docker tag roleplay-game:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest

echo "✅ 镜像推送完成"

# ------ Step 2: 创建安全组 ------
echo ""
echo ">>> Step 2/7: 创建安全组..."

ALB_SG_ID=$(aws ec2 create-security-group \
  --group-name roleplay-alb-sg \
  --description "ALB for roleplay game" \
  --vpc-id ${VPC_ID} \
  --region ${REGION} \
  --query 'GroupId' --output text)
echo "  ALB SG: ${ALB_SG_ID}"

# ALB 安全组：仅允许 CloudFront IP 范围
aws ec2 authorize-security-group-ingress \
  --group-id ${ALB_SG_ID} \
  --ip-permissions "IpProtocol=tcp,FromPort=80,ToPort=80,PrefixListIds=[{PrefixListId=${CF_PREFIX_LIST}}]" \
  --region ${REGION} > /dev/null

ECS_SG_ID=$(aws ec2 create-security-group \
  --group-name roleplay-ecs-sg \
  --description "ECS tasks for roleplay game" \
  --vpc-id ${VPC_ID} \
  --region ${REGION} \
  --query 'GroupId' --output text)
echo "  ECS SG: ${ECS_SG_ID}"

# ECS 安全组：仅允许 ALB 访问
aws ec2 authorize-security-group-ingress \
  --group-id ${ECS_SG_ID} \
  --protocol tcp \
  --port 5001 \
  --source-group ${ALB_SG_ID} \
  --region ${REGION} > /dev/null

echo "✅ 安全组创建完成"

# ------ Step 3: 创建 ALB + Target Group + Listener ------
echo ""
echo ">>> Step 3/7: 创建 ALB..."

ALB_ARN=$(aws elbv2 create-load-balancer \
  --name roleplay-alb \
  --subnets ${SUBNET_LIST} \
  --security-groups ${ALB_SG_ID} \
  --scheme internet-facing \
  --type application \
  --region ${REGION} \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns ${ALB_ARN} \
  --region ${REGION} \
  --query 'LoadBalancers[0].DNSName' --output text)
echo "  ALB DNS: ${ALB_DNS}"

TG_ARN=$(aws elbv2 create-target-group \
  --name roleplay-tg \
  --protocol HTTP \
  --port 5001 \
  --vpc-id ${VPC_ID} \
  --target-type ip \
  --health-check-path "/" \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --region ${REGION} \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Listener：默认返回 403，有正确 Header 才转发
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn ${ALB_ARN} \
  --protocol HTTP \
  --port 80 \
  --default-actions 'Type=fixed-response,FixedResponseConfig={StatusCode=403,ContentType=text/plain,MessageBody=Forbidden}' \
  --region ${REGION} \
  --query 'Listeners[0].ListenerArn' --output text)

aws elbv2 create-rule \
  --listener-arn ${LISTENER_ARN} \
  --priority 1 \
  --conditions "[{\"Field\":\"http-header\",\"HttpHeaderConfig\":{\"HttpHeaderName\":\"X-Custom-Header\",\"Values\":[\"${CF_SECRET}\"]}}]" \
  --actions "Type=forward,TargetGroupArn=${TG_ARN}" \
  --region ${REGION} > /dev/null

echo "✅ ALB 创建完成"

# ------ Step 4: CloudWatch 日志组 ------
echo ""
echo ">>> Step 4/7: 创建日志组..."

aws logs create-log-group \
  --log-group-name /ecs/roleplay-game \
  --region ${REGION} 2>/dev/null || true

echo "✅ 日志组就绪"

# ------ Step 5: 注册任务定义 ------
echo ""
echo ">>> Step 5/7: 注册任务定义..."

cat > /tmp/roleplay-task-def.json << EOF
{
  "family": "roleplay-game",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "${EXECUTION_ROLE}",
  "containerDefinitions": [
    {
      "name": "roleplay-game",
      "image": "${ECR_REPO}:latest",
      "portMappings": [{"containerPort": 5001, "protocol": "tcp"}],
      "environment": [{"name": "SECRET_KEY", "value": "${APP_SECRET}"}],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/roleplay-game",
          "awslogs-region": "${REGION}",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition \
  --cli-input-json file:///tmp/roleplay-task-def.json \
  --region ${REGION} > /dev/null

echo "✅ 任务定义注册完成"

# ------ Step 6: 创建 ECS 服务 ------
echo ""
echo ">>> Step 6/7: 创建 ECS 服务..."

aws ecs create-service \
  --cluster ${CLUSTER} \
  --service-name roleplay-game \
  --task-definition roleplay-game \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${SUBNETS}],securityGroups=[${ECS_SG_ID}],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=${TG_ARN},containerName=roleplay-game,containerPort=5001" \
  --region ${REGION} > /dev/null

echo "✅ ECS 服务创建完成"

# ------ Step 7: 创建 CloudFront ------
echo ""
echo ">>> Step 7/7: 创建 CloudFront 分配..."

CF_CONFIG=$(cat << EOF
{
  "CallerReference": "roleplay-$(date +%s)",
  "Comment": "Roleplay Game - 守门人的突围",
  "Enabled": true,
  "DefaultCacheBehavior": {
    "TargetOriginId": "roleplay-alb",
    "ViewerProtocolPolicy": "allow-all",
    "AllowedMethods": {
      "Quantity": 7,
      "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"],
      "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}
    },
    "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
    "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3",
    "Compress": true
  },
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "roleplay-alb",
        "DomainName": "${ALB_DNS}",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only"
        },
        "CustomHeaders": {
          "Quantity": 1,
          "Items": [
            {
              "HeaderName": "X-Custom-Header",
              "HeaderValue": "${CF_SECRET}"
            }
          ]
        }
      }
    ]
  },
  "DefaultRootObject": ""
}
EOF
)

CF_DOMAIN=$(aws cloudfront create-distribution \
  --distribution-config "${CF_CONFIG}" \
  --query 'Distribution.DomainName' --output text)

echo "✅ CloudFront 创建完成"

# ------ 完成 ------
echo ""
echo "============================================"
echo "  🎉 部署完成！"
echo "============================================"
echo ""
echo "  CloudFront: https://${CF_DOMAIN}"
echo "  ALB (直接访问会 403): http://${ALB_DNS}"
echo ""
echo "  ⏳ ECS 任务启动约需 1-2 分钟"
echo "  ⏳ CloudFront 分配生效约需 3-5 分钟"
echo ""
echo "  CF Secret (已自动配置): ${CF_SECRET}"
echo "============================================"
