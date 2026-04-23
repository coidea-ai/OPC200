#!/bin/bash
# OPC200 平台侧一键部署脚本
# 部署组件：Pushgateway + Prometheus + Alertmanager + Grafana
# 版本: 2026.1

set -euo pipefail

# ========== 颜色 ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${BLUE}ℹ️  $1${NC}"; }
ok()      { echo -e "${GREEN}✅ $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()     { echo -e "${RED}❌ $1${NC}" >&2; }
step()    { echo -e "${CYAN}▶ $1${NC}"; }

# ========== 默认值 ==========
DEFAULT_DEPLOY_DIR="/opt/opc200-platform"
DEFAULT_GRAFANA_PASS="$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)"
DEFAULT_RETENTION_DAYS="15"

# ========== 检查函数 ==========
check_root() {
    if [[ "$EUID" -ne 0 ]]; then
        err "请使用 root 或 sudo 运行此脚本"
        exit 1
    fi
}

check_docker() {
    step "检查 Docker 环境..."
    if ! command -v docker &>/dev/null; then
        err "Docker 未安装"
        info "安装命令: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    if ! docker compose version &>/dev/null && ! docker-compose version &>/dev/null; then
        err "Docker Compose 未安装"
        exit 1
    fi
    ok "Docker 环境正常 ($(docker --version | awk '{print $3}' | tr -d ','))"
}

check_ports() {
    step "检查端口占用..."
    local ports=(9090 9091 9093 3000)
    local occupied=()
    for p in "${ports[@]}"; do
        if ss -tlnp | awk '{print $4}' | grep -q ":$p$"; then
            occupied+=("$p")
        fi
    done
    if [[ ${#occupied[@]} -gt 0 ]]; then
        warn "以下端口已被占用: ${occupied[*]}"
        read -rp "是否继续? [y/N]: " confirm
        [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
    fi
}

# ========== 交互式配置 ==========
prompt() {
    local var_name="$1"
    local message="$2"
    local default="${3:-}"
    local is_secret="${4:-false}"

    if [[ -n "$default" ]]; then
        message="$message [默认: $default]"
    fi
    message="$message: "

    if [[ "$is_secret" == "true" ]]; then
        read -rsp "$message" value
        echo
    else
        read -rp "$message" value
    fi

    if [[ -z "$value" && -n "$default" ]]; then
        value="$default"
    fi

    printf -v "$var_name" '%s' "$value"
}

collect_config() {
    step "配置部署参数（直接回车使用默认值）"
    echo

    prompt DEPLOY_DIR "部署目录" "$DEFAULT_DEPLOY_DIR"
    prompt EXTERNAL_HOST "服务器访问地址（IP 或域名，用于 Alertmanager 和 Grafana）" ""
    if [[ -z "$EXTERNAL_HOST" ]]; then
        EXTERNAL_HOST=$(hostname -I | awk '{print $1}')
        info "自动检测为: $EXTERNAL_HOST"
    fi
    prompt GRAFANA_ADMIN_PASS "Grafana 管理员密码" "$DEFAULT_GRAFANA_PASS" true
    prompt RETENTION "Prometheus 数据保留天数" "$DEFAULT_RETENTION_DAYS"

    echo
    step "配置告警邮箱（Alertmanager）"
    prompt SMTP_HOST "SMTP 服务器" "smtp.qq.com:587"
    prompt SMTP_USER "发件邮箱" ""
    prompt SMTP_PASS "邮箱授权码/密码" "" true
    prompt ALERT_TO "告警收件人邮箱" "${SMTP_USER:-}"

    echo
    step "配置确认"
    echo "  部署目录:     $DEPLOY_DIR"
    echo "  访问地址:     $EXTERNAL_HOST"
    echo "  Grafana密码:  ${GRAFANA_ADMIN_PASS:0:4}****"
    echo "  数据保留:     ${PROM_RETENTION}天"
    echo "  SMTP服务器:   $SMTP_HOST"
    echo "  发件邮箱:     $SMTP_USER"
    echo "  告警收件人:   $ALERT_TO"
    echo
    read -rp "确认部署? [Y/n]: " confirm
    if [[ "$confirm" =~ ^[Nn]$ ]]; then
        err "已取消"
        exit 1
    fi
}

# ========== 生成配置文件 ==========
generate_docker_compose() {
    step "生成 docker-compose.yml..."
    cat > "$DEPLOY_DIR/docker-compose.yml" <<'EOF'
version: '3.8'

services:
  pushgateway:
    image: prom/pushgateway:v1.7.0
    container_name: opc200-pushgateway
    ports:
      - "9091:9091"
    command:
      - --persistence.file=/data/metrics
      - --persistence.interval=5m
    volumes:
      - pushgateway-data:/data
    networks:
      - opc200-platform
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:v2.49.1
    container_name: opc200-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/rules:/etc/prometheus/rules:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=${RETENTION}d'
      - '--web.enable-lifecycle'
      - '--alertmanager.url=http://opc200-alertmanager:9093'
    networks:
      - opc200-platform
    restart: unless-stopped
    depends_on:
      - pushgateway
      - alertmanager

  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: opc200-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager-data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=http://${EXTERNAL_HOST}:9093'
    networks:
      - opc200-platform
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.3.1
    container_name: opc200-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASS}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=http://${EXTERNAL_HOST}:3000
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    networks:
      - opc200-platform
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  pushgateway-data:
  prometheus-data:
  grafana-data:
  alertmanager-data:

networks:
  opc200-platform:
    driver: bridge
EOF
    ok "docker-compose.yml 已生成"
}

generate_prometheus_config() {
    step "生成 Prometheus 配置..."
    mkdir -p "$DEPLOY_DIR/prometheus/rules"

    cat > "$DEPLOY_DIR/prometheus/prometheus.yml" <<'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: 'pushgateway'
    static_configs:
      - targets: ['pushgateway:9091']
    honor_labels: true

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'alertmanager'
    static_configs:
      - targets: ['alertmanager:9093']
EOF

    cat > "$DEPLOY_DIR/prometheus/rules/opc200.yml" <<'EOF'
groups:
  - name: opc200-default
    rules:
      - alert: AgentPushMissing
        expr: absent(up{job="pushgateway"})
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Agent 指标推送中断"
          description: "Pushgateway 超过 5 分钟未收到任何指标推送"

      - alert: HighMemoryUsage
        expr: opc200_memory_usage_percent > 85
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Agent 内存使用率过高"
          description: "Agent {{ $labels.agent_id }} 内存使用率超过 85%"

      - alert: CriticalMemoryUsage
        expr: opc200_memory_usage_percent > 95
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Agent 内存使用危险"
          description: "Agent {{ $labels.agent_id }} 内存使用率超过 95%"

      - alert: AgentOffline
        expr: time() - opc200_last_heartbeat_timestamp > 300
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Agent 离线"
          description: "Agent {{ $labels.agent_id }} 超过 5 分钟未上报心跳"
EOF
    ok "Prometheus 配置已生成"
}

generate_alertmanager_config() {
    step "生成 Alertmanager 配置..."
    mkdir -p "$DEPLOY_DIR/alertmanager"

    cat > "$DEPLOY_DIR/alertmanager/alertmanager.yml" <<EOF
global:
  smtp_smarthost: '${SMTP_HOST:-smtp.qq.com:587}'
  smtp_from: '${SMTP_USER:-opc200@example.com}'
  smtp_auth_username: '${SMTP_USER:-opc200@example.com}'
  smtp_auth_password: '${SMTP_PASS:-placeholder}'
  smtp_require_tls: true

route:
  group_by: ['alertname', 'job']
  group_wait: 10s
  group_interval: 4h
  repeat_interval: 4h
  receiver: 'opc200-email'

  routes:
    - match:
        severity: critical
      receiver: 'opc200-feishu-p0'
      group_wait: 10s
      continue: true
    - match:
        severity: warning
      receiver: 'opc200-email-p1'
      group_wait: 10s
      group_interval: 4h
      repeat_interval: 4h
      continue: true

receivers:
  - name: 'opc200-feishu-p0'
    webhook_configs:
      - url: 'http://localhost:5000/webhook/feishu'
        send_resolved: true

  - name: 'opc200-email-p0'
    email_configs:
      - to: '${ALERT_TO:-admin@example.com}'
        send_resolved: true
        headers:
          Subject: '[P0] OPC200 Alert: {{ .GroupLabels.alertname }}'
        html: '<h2>OPC200 P0 告警</h2><pre>{{ .CommonAnnotations.summary }}</pre><p>{{ .CommonAnnotations.description }}</p>'

  - name: 'opc200-email-p1'
    email_configs:
      - to: '${ALERT_TO:-admin@example.com}'
        send_resolved: true
        headers:
          Subject: '[P1] OPC200 Alert: {{ .GroupLabels.alertname }}'
        html: '<h2>OPC200 P1 告警</h2><pre>{{ .CommonAnnotations.summary }}</pre><p>{{ .CommonAnnotations.description }}</p>'

  - name: 'opc200-email'
    email_configs:
      - to: '${ALERT_TO:-admin@example.com}'
        send_resolved: true
        headers:
          Subject: 'OPC200 Alert: {{ .GroupLabels.alertname }}'
        html: '<h2>OPC200 告警</h2><pre>{{ .CommonAnnotations.summary }}</pre><p>{{ .CommonAnnotations.description }}</p>'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['job']
EOF
    chmod 644 "$DEPLOY_DIR/alertmanager/alertmanager.yml"
    ok "Alertmanager 配置已生成"
}

generate_grafana_provisioning() {
    step "生成 Grafana 预配置..."
    mkdir -p "$DEPLOY_DIR/grafana/provisioning/datasources"
    mkdir -p "$DEPLOY_DIR/grafana/provisioning/dashboards"

    cat > "$DEPLOY_DIR/grafana/provisioning/datasources/datasource.yml" <<'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF

    cat > "$DEPLOY_DIR/grafana/provisioning/dashboards/dashboard.yml" <<'EOF'
apiVersion: 1
providers:
  - name: 'OPC200'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    # 生成基础 overview dashboard JSON
    cat > "$DEPLOY_DIR/grafana/provisioning/dashboards/opc200-overview.json" <<'DASHBOARD_EOF'
{
  "dashboard": {
    "id": null,
    "title": "OPC200 Overview",
    "tags": ["opc200"],
    "timezone": "Asia/Shanghai",
    "panels": [
      {
        "id": 1,
        "title": "Agent 在线数",
        "type": "stat",
        "targets": [{"expr": "count(opc200_last_heartbeat_timestamp)", "legendFormat": "agents"}],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Pushgateway 指标数",
        "type": "stat",
        "targets": [{"expr": "pushgateway_http_requests_total", "legendFormat": "requests"}],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      }
    ],
    "time": {"from": "now-1h", "to": "now"}
  },
  "overwrite": true
}
DASHBOARD_EOF
    ok "Grafana 预配置已生成"
}

generate_env() {
    step "生成 .env 文件..."
    cat > "$DEPLOY_DIR/.env" <<EOF
# OPC200 Platform 环境变量
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')

EXTERNAL_HOST=${EXTERNAL_HOST}
GRAFANA_PASS=${GRAFANA_ADMIN_PASS}
RETENTION=${RETENTION}
SMTP_HOST=${SMTP_HOST}
SMTP_USER=${SMTP_USER}
EOF
    chmod 600 "$DEPLOY_DIR/.env"
    ok ".env 已生成"
}

# ========== 部署 ==========
deploy() {
    step "启动服务..."
    cd "$DEPLOY_DIR"

    # 用 envsubst 替换 docker-compose.yml 中的变量
    export EXTERNAL_HOST GRAFANA_ADMIN_PASS RETENTION
    envsubst '$EXTERNAL_HOST $GRAFANA_ADMIN_PASS $RETENTION' < docker-compose.yml > docker-compose.yml.tmp
    mv docker-compose.yml.tmp docker-compose.yml

    if docker compose version &>/dev/null; then
        docker compose up -d
    else
        docker-compose up -d
    fi
    ok "服务启动完成"
}

# ========== 完成信息 ==========
show_summary() {
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}       OPC200 平台侧部署完成${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo "📍 访问地址:"
    echo "   Grafana:        http://${EXTERNAL_HOST}:3000"
    echo "   Prometheus:     http://${EXTERNAL_HOST}:9090"
    echo "   Alertmanager:   http://${EXTERNAL_HOST}:9093"
    echo "   Pushgateway:    http://${EXTERNAL_HOST}:9091"
    echo
    echo "🔐 Grafana 管理员:"
    echo "   用户名: admin"
    echo "   密码:   ${GRAFANA_ADMIN_PASS:0:4}****"
    echo "   (完整密码保存在 ${DEPLOY_DIR}/.env)"
    echo
    echo "📁 部署目录: ${DEPLOY_DIR}"
    echo
    echo "🛠 常用命令:"
    echo "   cd ${DEPLOY_DIR}"
    echo "   docker compose ps        # 查看服务状态"
    echo "   docker compose logs -f   # 查看日志"
    echo "   docker compose down      # 停止服务"
    echo
    echo "📧 告警邮件配置:"
    echo "   SMTP: ${SMTP_HOST}"
    echo "   发件: ${SMTP_USER}"
    echo "   收件: ${ALERT_TO}"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ========== 主流程 ==========
main() {
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "       OPC200 平台侧一键部署"
    echo "       Pushgateway + Prometheus + Alertmanager + Grafana"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo

    check_root
    check_docker
    check_ports
    collect_config

    info "创建部署目录: $DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR"

    generate_docker_compose
    generate_prometheus_config
    generate_alertmanager_config
    generate_grafana_provisioning
    generate_env
    deploy
    show_summary
}

main "$@"
