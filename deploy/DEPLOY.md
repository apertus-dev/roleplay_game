# 《守门人的突围》部署指南

> 目标架构：CloudFront → ALB → ECS Fargate (东京区域)
> 
> ALB 仅允许 CloudFront 访问

## 环境信息

| 资源 | 值 |
|------|-----|
| AWS Account | 722977099337 |
| Region | ap-northeast-1 |
| ECS Cluster | jpn-start-ecs-cluster |
| VPC | vpc-0a0276401252ad557 |
| 子网 | subnet-0624f33aa92cdb358, subnet-05fe69b6f7cc34a91, subnet-01e941ac776ef1073 |
| ECR 仓库 | 722977099337.dkr.ecr.ap-northeast-1.amazonaws.com/roleplay-game |
| 执行角色 | arn:aws:iam::722977099337:role/ecsTaskExecutionRole |

---

## Step 1: 安装 Docker

```bash
brew install --cask docker
```

安装后打开 Docker Desktop，等状态栏图标显示 "Docker Desktop is running"。

---

## Step 2: 构建并推送镜像

```bash
cd /Users/glencai/Documents/kiro/roleplay_game

# ECR 登录
aws ecr get-login-password --region ap-northeast-1 | \
  docker login --username AWS --password-stdin 722977099337.dkr.ecr.ap-northeast-1.amazonaws.com

# 构建镜像（M 系列 Mac 需要指定平台）
docker build --platform linux/amd64 -t roleplay-game .

# 打标签
docker tag roleplay-game:latest 722977099337.dkr.ecr.ap-northeast-1.amazonaws.com/roleplay-game:latest

# 推送
docker push 722977099337.dkr.ecr.ap-northeast-1.amazonaws.com/roleplay-game:latest
```

---

## Step 3: 创建安全组

### 3.1 ALB 安全组（暂时开放 80，后面会改为仅 CloudFront）

```bash
aws ec2 create-security-group \
  --group-name roleplay-alb-sg \
  --description "ALB for roleplay game" \
  --vpc-id vpc-0a0276401252ad557 \
  --region ap-northeast-1
```

记下输出的 `GroupId`，下面用 `ALB_SG_ID` 代替。

```bash
aws ec2 authorize-security-group-ingress \
  --group-id ALB_SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region ap-northeast-1
```

### 3.2 ECS 任务安全组（仅允许 ALB 访问）

```bash
aws ec2 create-security-group \
  --group-name roleplay-ecs-sg \
  --description "ECS tasks for roleplay game" \
  --vpc-id vpc-0a0276401252ad557 \
  --region ap-northeast-1
```

记下输出的 `GroupId`，下面用 `ECS_SG_ID` 代替。

```bash
aws ec2 authorize-security-group-ingress \
  --group-id ECS_SG_ID \
  --protocol tcp \
  --port 5001 \
  --source-group ALB_SG_ID \
  --region ap-northeast-1
```

---

## Step 4: 创建 ALB + Target Group

### 4.1 创建 ALB

```bash
aws elbv2 create-load-balancer \
  --name roleplay-alb \
  --subnets subnet-0624f33aa92cdb358 subnet-05fe69b6f7cc34a91 subnet-01e941ac776ef1073 \
  --security-groups ALB_SG_ID \
  --scheme internet-facing \
  --type application \
  --region ap-northeast-1
```

记下输出的 `LoadBalancerArn` 和 `DNSName`。

### 4.2 创建 Target Group

```bash
aws elbv2 create-target-group \
  --name roleplay-tg \
  --protocol HTTP \
  --port 5001 \
  --vpc-id vpc-0a0276401252ad557 \
  --target-type ip \
  --health-check-path "/" \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --region ap-northeast-1
```

记下输出的 `TargetGroupArn`。

### 4.3 创建 Listener

```bash
aws elbv2 create-listener \
  --load-balancer-arn ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=TARGET_GROUP_ARN \
  --region ap-northeast-1
```

---

## Step 5: 创建 CloudWatch 日志组

```bash
aws logs create-log-group \
  --log-group-name /ecs/roleplay-game \
  --region ap-northeast-1
```

---

## Step 6: 注册任务定义并创建 ECS 服务

### 6.1 注册任务定义

先修改 `deploy/task-definition.json` 中的 `SECRET_KEY` 为一个随机字符串，然后：

```bash
aws ecs register-task-definition \
  --cli-input-json file://deploy/task-definition.json \
  --region ap-northeast-1
```

### 6.2 创建服务

```bash
aws ecs create-service \
  --cluster jpn-start-ecs-cluster \
  --service-name roleplay-game \
  --task-definition roleplay-game \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-0624f33aa92cdb358,subnet-05fe69b6f7cc34a91,subnet-01e941ac776ef1073],securityGroups=[ECS_SG_ID],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=TARGET_GROUP_ARN,containerName=roleplay-game,containerPort=5001" \
  --region ap-northeast-1
```

### 6.3 验证

等 1-2 分钟，检查服务状态：

```bash
aws ecs describe-services \
  --cluster jpn-start-ecs-cluster \
  --services roleplay-game \
  --query "services[0].{status:status,running:runningCount,desired:desiredCount}" \
  --region ap-northeast-1
```

此时访问 ALB 的 DNSName 应该能看到游戏页面。

---

## Step 7: 创建 CloudFront 分配

```bash
aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "roleplay-game-'$(date +%s)'",
    "Comment": "Roleplay Game",
    "Enabled": true,
    "DefaultCacheBehavior": {
      "TargetOriginId": "roleplay-alb",
      "ViewerProtocolPolicy": "allow-all",
      "AllowedMethods": {
        "Quantity": 7,
        "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"],
        "CachedMethods": { "Quantity": 2, "Items": ["GET","HEAD"] }
      },
      "ForwardedValues": {
        "QueryString": true,
        "Cookies": { "Forward": "all" },
        "Headers": { "Quantity": 1, "Items": ["Host"] }
      },
      "MinTTL": 0,
      "DefaultTTL": 0,
      "MaxTTL": 0
    },
    "Origins": {
      "Quantity": 1,
      "Items": [
        {
          "Id": "roleplay-alb",
          "DomainName": "ALB_DNS_NAME",
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
                "HeaderValue": "CHANGE_ME_TO_A_SECRET_VALUE"
              }
            ]
          }
        }
      ]
    },
    "DefaultRootObject": ""
  }'
```

⚠️ 把 `ALB_DNS_NAME` 替换为 Step 4 中的 ALB DNS 名称。
⚠️ 把 `CHANGE_ME_TO_A_SECRET_VALUE` 替换为一个随机密钥（自己记住，下一步要用）。

记下输出的 CloudFront `DomainName`（形如 dxxxxx.cloudfront.net）。

---

## Step 8: 锁定 ALB 仅允许 CloudFront 访问

### 8.1 修改 ALB 安全组：替换为 CloudFront 前缀列表

```bash
# 先删除之前的 0.0.0.0/0 规则
aws ec2 revoke-security-group-ingress \
  --group-id ALB_SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region ap-northeast-1

# 添加 CloudFront 托管前缀列表（AWS 官方维护）
aws ec2 authorize-security-group-ingress \
  --group-id ALB_SG_ID \
  --ip-permissions "IpProtocol=tcp,FromPort=80,ToPort=80,PrefixListIds=[{PrefixListId=pl-58a04531}]" \
  --region ap-northeast-1
```

> `pl-58a04531` 是 CloudFront 在 ap-northeast-1 的托管前缀列表。

### 8.2 ALB 添加自定义 Header 验证规则

修改 ALB Listener 规则，只放行带有正确自定义 Header 的请求：

```bash
# 获取 Listener ARN
aws elbv2 describe-listeners \
  --load-balancer-arn ALB_ARN \
  --query "Listeners[0].ListenerArn" \
  --output text \
  --region ap-northeast-1
```

```bash
# 修改默认规则：无自定义 Header 返回 403
aws elbv2 modify-listener \
  --listener-arn LISTENER_ARN \
  --default-actions Type=fixed-response,FixedResponseConfig="{StatusCode=403,ContentType=text/plain,MessageBody=Forbidden}" \
  --region ap-northeast-1

# 添加规则：有正确 Header 才转发
aws elbv2 create-rule \
  --listener-arn LISTENER_ARN \
  --priority 1 \
  --conditions '[{"Field":"http-header-config","HttpHeaderConfig":{"HttpHeaderName":"X-Custom-Header","Values":["CHANGE_ME_TO_A_SECRET_VALUE"]}}]' \
  --actions Type=forward,TargetGroupArn=TARGET_GROUP_ARN \
  --region ap-northeast-1
```

⚠️ `CHANGE_ME_TO_A_SECRET_VALUE` 必须和 Step 7 中 CloudFront 设置的值一致。

---

## 验证

1. 访问 CloudFront 域名 `https://dxxxxx.cloudfront.net` → ✅ 正常显示游戏
2. 直接访问 ALB DNS → ❌ 返回 403 Forbidden

---

## 后续更新部署

代码更新后重新构建推送即可：

```bash
docker build --platform linux/amd64 -t roleplay-game .
docker tag roleplay-game:latest 722977099337.dkr.ecr.ap-northeast-1.amazonaws.com/roleplay-game:latest
docker push 722977099337.dkr.ecr.ap-northeast-1.amazonaws.com/roleplay-game:latest

# 强制重新部署
aws ecs update-service \
  --cluster jpn-start-ecs-cluster \
  --service roleplay-game \
  --force-new-deployment \
  --region ap-northeast-1
```
