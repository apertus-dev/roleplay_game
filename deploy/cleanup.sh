#!/bin/bash
set -e

REGION="ap-northeast-1"
CLUSTER="jpn-start-ecs-cluster"

echo ">>> 删除 ECS 服务..."
aws ecs update-service --cluster ${CLUSTER} --service roleplay-game --desired-count 0 --region ${REGION} > /dev/null 2>&1 || true
aws ecs delete-service --cluster ${CLUSTER} --service roleplay-game --force --region ${REGION} > /dev/null 2>&1 || true

echo ">>> 删除 ALB..."
ALB_ARN=$(aws elbv2 describe-load-balancers --names roleplay-alb --region ${REGION} --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || true)
if [ "$ALB_ARN" != "None" ] && [ -n "$ALB_ARN" ]; then
  LISTENER_ARNS=$(aws elbv2 describe-listeners --load-balancer-arn ${ALB_ARN} --region ${REGION} --query 'Listeners[*].ListenerArn' --output text 2>/dev/null || true)
  for arn in ${LISTENER_ARNS}; do
    aws elbv2 delete-listener --listener-arn ${arn} --region ${REGION} 2>/dev/null || true
  done
  aws elbv2 delete-load-balancer --load-balancer-arn ${ALB_ARN} --region ${REGION} 2>/dev/null || true
fi

echo ">>> 删除 Target Group..."
TG_ARN=$(aws elbv2 describe-target-groups --names roleplay-tg --region ${REGION} --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null || true)
if [ "$TG_ARN" != "None" ] && [ -n "$TG_ARN" ]; then
  aws elbv2 delete-target-group --target-group-arn ${TG_ARN} --region ${REGION} 2>/dev/null || true
fi

echo ">>> 删除 CloudFront（需手动，因为要先 disable）..."
echo "  请到 AWS Console 手动 disable 并删除 CloudFront 分配"

echo ">>> 删除安全组（等待 ALB 完全删除后）..."
echo "  等待 60 秒..."
sleep 60
ALB_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=roleplay-alb-sg" --region ${REGION} --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
ECS_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=roleplay-ecs-sg" --region ${REGION} --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
[ "$ECS_SG" != "None" ] && [ -n "$ECS_SG" ] && aws ec2 delete-security-group --group-id ${ECS_SG} --region ${REGION} 2>/dev/null || true
[ "$ALB_SG" != "None" ] && [ -n "$ALB_SG" ] && aws ec2 delete-security-group --group-id ${ALB_SG} --region ${REGION} 2>/dev/null || true

echo ">>> 删除日志组..."
aws logs delete-log-group --log-group-name /ecs/roleplay-game --region ${REGION} 2>/dev/null || true

echo ">>> 删除 ECR 镜像..."
aws ecr delete-repository --repository-name roleplay-game --force --region ${REGION} 2>/dev/null || true

echo ""
echo "✅ 清理完成（CloudFront 需手动删除）"
