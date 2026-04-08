#!/bin/bash
#===============================================================================
# OPC200 Cloud Deployment Script
# 用途: 云端客户 Gateway 部署
# 执行位置: 云端 Kubernetes / Docker Compose
#===============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 默认配置
OPC_ID=""
FEISHU_TOKEN=""
NAMESPACE="opc200-cloud"
REPLICAS=1

show_help() {
    cat << EOF
OPC200 Cloud Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -i, --id ID          客户ID (如: OPC-151)
    -f, --feishu TOKEN   飞书 Bot Token
    -n, --namespace NS   Kubernetes Namespace (默认: opc200-cloud)
    -r, --replicas N     副本数 (默认: 1)
    -h, --help          显示此帮助

示例:
    $0 -i OPC-151 -f feishu-bot-token
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--id)
                OPC_ID="$2"
                shift 2
                ;;
            -f|--feishu)
                FEISHU_TOKEN="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--replicas)
                REPLICAS="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    if [[ -z "$OPC_ID" ]]; then
        log_error "缺少客户ID (-i, --id)"
        exit 1
    fi
}

# 创建 Namespace
create_namespace() {
    log_info "创建 Namespace: $NAMESPACE"
    
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Namespace 就绪"
}

# 创建 ConfigMap
create_configmap() {
    log_info "创建 ConfigMap"
    
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: opc200-${OPC_ID,,}-config
  namespace: ${NAMESPACE}
data:
  gateway.yml: |
    customer:
      id: ${OPC_ID}
      name: "Cloud Customer ${OPC_ID#OPC-}"
      mode: cloud-hosted
      
    gateway:
      id: gateway-${OPC_ID,,}
      
    channels:
      feishu:
        enabled: true
        bot_token: "${FEISHU_TOKEN}"
        
    telemetry:
      enabled: true
      endpoint: https://monitor.opc200.co/api/v1/metrics
EOF

    log_success "ConfigMap 创建完成"
}

# 创建 Secret
create_secret() {
    log_info "创建 Secret"
    
    kubectl create secret generic opc200-${OPC_ID,,}-secrets \
        --namespace="$NAMESPACE" \
        --from-literal=feishu-token="$FEISHU_TOKEN" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Secret 创建完成"
}

# 创建 Deployment
create_deployment() {
    log_info "创建 Deployment"
    
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opc200-${OPC_ID,,}-gateway
  namespace: ${NAMESPACE}
  labels:
    app: opc200-gateway
    customer: ${OPC_ID}
spec:
  replicas: ${REPLICAS}
  selector:
    matchLabels:
      app: opc200-gateway
      customer: ${OPC_ID}
  template:
    metadata:
      labels:
        app: opc200-gateway
        customer: ${OPC_ID}
    spec:
      containers:
      - name: gateway
        image: ghcr.io/openclaw/openclaw:latest
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: OPC_ID
          value: "${OPC_ID}"
        - name: NODE_ENV
          value: "production"
        - name: DATA_DIR
          value: "/data"
        volumeMounts:
        - name: config
          mountPath: /config.yml
          subPath: gateway.yml
        - name: data
          mountPath: /data
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: opc200-${OPC_ID,,}-config
      - name: data
        persistentVolumeClaim:
          claimName: opc200-${OPC_ID,,}-data
EOF

    log_success "Deployment 创建完成"
}

# 创建 PVC
create_pvc() {
    log_info "创建 PVC"
    
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: opc200-${OPC_ID,,}-data
  namespace: ${NAMESPACE}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
EOF

    log_success "PVC 创建完成"
}

# 创建 Service
create_service() {
    log_info "创建 Service"
    
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: opc200-${OPC_ID,,}-service
  namespace: ${NAMESPACE}
spec:
  selector:
    app: opc200-gateway
    customer: ${OPC_ID}
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: ClusterIP
EOF

    log_success "Service 创建完成"
}

# 等待部署完成
wait_for_deployment() {
    log_info "等待部署完成..."
    
    kubectl rollout status deployment/opc200-${OPC_ID,,}-gateway \
        --namespace="$NAMESPACE" \
        --timeout=300s
    
    log_success "部署完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署"
    
    # 检查 Pod 状态
    local pod_name=$(kubectl get pods \
        --namespace="$NAMESPACE" \
        --selector="customer=${OPC_ID}" \
        -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -z "$pod_name" ]]; then
        log_error "未找到 Pod"
        return 1
    fi
    
    log_info "Pod: $pod_name"
    
    # 检查健康状态
    if kubectl exec "$pod_name" --namespace="$NAMESPACE" -- wget -qO- http://localhost:8080/health > /dev/null 2>&1; then
        log_success "健康检查通过"
    else
        log_warn "健康检查未通过"
    fi
}

# 主函数
main() {
    log_info "OPC200 Cloud Deployment"
    log_info "======================="
    
    parse_args "$@"
    
    log_info "客户ID: $OPC_ID"
    log_info "Namespace: $NAMESPACE"
    log_info "副本数: $REPLICAS"
    
    create_namespace
    create_configmap
    create_secret
    create_pvc
    create_deployment
    create_service
    wait_for_deployment
    verify_deployment
    
    log_success "======================="
    log_success "云端部署完成!"
    log_success "======================="
    
    echo ""
    echo "部署信息:"
    echo "  客户ID: $OPC_ID"
    echo "  Namespace: $NAMESPACE"
    echo "  Service: opc200-${OPC_ID,,}-service"
    echo ""
    echo "常用命令:"
    echo "  查看Pod: kubectl get pods -n $NAMESPACE -l customer=$OPC_ID"
    echo "  查看日志: kubectl logs -n $NAMESPACE -l customer=$OPC_ID -f"
    echo "  扩缩容: kubectl scale deployment opc200-${OPC_ID,,}-gateway -n $NAMESPACE --replicas=2"
}

main "$@"
