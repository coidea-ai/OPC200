#!/bin/bash
# OPC200 仿真测试快速启动脚本

set -e

# 默认配置
LOCAL_AGENTS=20      # 默认20个本地实例（快速测试）
CLOUD_AGENTS=10      # 默认10个云端实例
DURATION_HOURS=1     # 默认运行1小时
MODE="quick"         # quick / full

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    cat << EOF
OPC200 仿真测试快速启动

用法: $0 [选项]

选项:
    -l, --local N       本地实例数量 (默认: 20)
    -c, --cloud N       云端实例数量 (默认: 10)
    -d, --duration H    运行时长小时数 (默认: 1)
    -m, --mode MODE     运行模式: quick/full/stress (默认: quick)
    -h, --help          显示帮助

模式说明:
    quick   - 快速验证 (20本地+10云端, 1小时)
    full    - 全量测试 (150本地+50云端, 168小时/7天)
    stress  - 压力测试 (200本地+100云端, 24小时)

示例:
    $0                    # 快速测试
    $0 -m full            # 7×24全量测试
    $0 -l 50 -c 20 -d 4   # 自定义配置

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -l|--local)
                LOCAL_AGENTS="$2"
                shift 2
                ;;
            -c|--cloud)
                CLOUD_AGENTS="$2"
                shift 2
                ;;
            -d|--duration)
                DURATION_HOURS="$2"
                shift 2
                ;;
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 根据模式设置参数
    case $MODE in
        full)
            LOCAL_AGENTS=150
            CLOUD_AGENTS=50
            DURATION_HOURS=168
            ;;
        stress)
            LOCAL_AGENTS=200
            CLOUD_AGENTS=100
            DURATION_HOURS=24
            ;;
        quick|*)
            # 使用默认值
            ;;
    esac
}

check_prerequisites() {
    echo "🔍 检查依赖..."
    
    command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ 需要 Docker${NC}"; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}❌ 需要 Docker Compose${NC}"; exit 1; }
    command -v python3 >/dev/null 2>&1 || { echo -e "${RED}❌ 需要 Python3${NC}"; exit 1; }
    
    echo -e "${GREEN}✅ 依赖检查通过${NC}"
}

generate_compose() {
    echo "📝 生成 Docker Compose 配置..."
    
    mkdir -p simulation/config
    
    cat > simulation/docker-compose.simulation.yml << EOF
version: '3.8'

services:
  gateway:
    image: openclaw/gateway:2026.3
    ports:
      - "8080:8080"
    environment:
      - SIMULATION_MODE=true
      - MAX_AGENTS=$((LOCAL_AGENTS + 10))
    networks:
      - opc-sim

  agent-local:
    image: openclaw/agent:2026.3
    deploy:
      replicas: ${LOCAL_AGENTS}
    environment:
      - AGENT_MODE=local
      - GATEWAY_URL=http://gateway:8080
      - SIMULATION=true
    depends_on:
      - gateway
    networks:
      - opc-sim
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - opc-sim

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    networks:
      - opc-sim

networks:
  opc-sim:
    driver: bridge
EOF

    # 生成 Prometheus 配置
    cat > simulation/config/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'opc-agents'
    static_configs:
      - targets: ['gateway:8080']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
EOF

    echo -e "${GREEN}✅ 配置生成完成${NC}"
}

generate_load_generator() {
    echo "📝 生成负载生成器..."
    
    mkdir -p simulation
    
    cat > simulation/load_generator.py << 'PYEOF'
#!/usr/bin/env python3
"""简化版负载生成器."""

import asyncio
import random
import aiohttp
import argparse
from datetime import datetime


async def generate_load(agent_count: int, duration_hours: int, gateway_url: str):
    """生成负载."""
    print(f"[{datetime.now()}] 启动负载生成器")
    print(f"  目标: {agent_count} 个实例")
    print(f"  时长: {duration_hours} 小时")
    print(f"  网关: {gateway_url}")
    
    end_time = asyncio.get_event_loop().time() + (duration_hours * 3600)
    request_count = 0
    error_count = 0
    
    while asyncio.get_event_loop().time() < end_time:
        tasks = []
        
        # 每个周期发送随机数量请求
        for _ in range(random.randint(1, min(10, agent_count))):
            task = send_request(gateway_url)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        request_count += len(results)
        error_count += sum(1 for r in results if isinstance(r, Exception))
        
        if request_count % 100 == 0:
            print(f"[{datetime.now()}] 已发送 {request_count} 请求, 错误 {error_count}")
        
        # 每秒一个周期
        await asyncio.sleep(1)
    
    print(f"[{datetime.now()}] 负载生成完成")
    print(f"  总请求: {request_count}")
    print(f"  错误数: {error_count}")
    print(f"  错误率: {(error_count/request_count)*100:.2f}%")


async def send_request(gateway_url: str):
    """发送请求."""
    skills = ["journal_record", "pattern_analyze", "task_create", "insight_generate"]
    skill = random.choice(skills)
    
    payload = {
        "intent": skill,
        "content": f"Simulation request at {datetime.now()}",
        "customer_id": f"SIM-{random.randint(1, 1000)}"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{gateway_url}/skill",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return await resp.json()
        except Exception as e:
            return e


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", type=int, default=20)
    parser.add_argument("--duration", type=int, default=1)
    parser.add_argument("--gateway", default="http://localhost:8080")
    args = parser.parse_args()
    
    asyncio.run(generate_load(args.agents, args.duration, args.gateway))
PYEOF

    chmod +x simulation/load_generator.py
    echo -e "${GREEN}✅ 负载生成器生成完成${NC}"
}

deploy() {
    echo ""
    echo "🚀 部署仿真环境"
    echo "=============="
    echo -e "${BLUE}本地实例:${NC} ${LOCAL_AGENTS}"
    echo -e "${BLUE}云端实例:${NC} ${CLOUD_AGENTS}"
    echo -e "${BLUE}运行时长:${NC} ${DURATION_HOURS}小时"
    echo ""
    
    # 启动服务
    cd simulation
    docker-compose -f docker-compose.simulation.yml up -d
    cd ..
    
    echo ""
    echo -e "${GREEN}✅ 服务启动完成${NC}"
    echo ""
    echo "访问地址:"
    echo "  - 网关:     http://localhost:8080"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana:  http://localhost:3000 (admin/admin)"
    echo ""
    
    # 启动负载生成器
    echo "🎯 启动负载生成..."
    python3 simulation/load_generator.py \
        --agents ${LOCAL_AGENTS} \
        --duration ${DURATION_HOURS} \
        --gateway http://localhost:8080 &
    
    LOAD_PID=$!
    
    echo ""
    echo "负载生成器 PID: $LOAD_PID"
    echo ""
    
    # 等待运行时间
    echo "⏱️  运行中... (按 Ctrl+C 提前结束)"
    sleep ${DURATION_HOURS}h &
    WAIT_PID=$!
    
    trap "echo ''; echo '收到中断信号，正在清理...'; kill $LOAD_PID $WAIT_PID 2>/dev/null; cleanup; exit 0" INT
    
    wait $WAIT_PID 2>/dev/null
    
    cleanup
}

cleanup() {
    echo ""
    echo "🧹 清理环境..."
    cd simulation
    docker-compose -f docker-compose.simulation.yml down
    cd ..
    echo -e "${GREEN}✅ 清理完成${NC}"
}

show_summary() {
    echo ""
    echo "================================"
    echo "✅ 仿真测试完成"
    echo "================================"
    echo ""
    echo "查看结果:"
    echo "  - Grafana: http://localhost:3000"
    echo "  - Prometheus: http://localhost:9090"
    echo ""
}

# 主流程
main() {
    parse_args "$@"
    
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║     OPC200 大规模仿真测试环境           ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
    
    check_prerequisites
    generate_compose
    generate_load_generator
    deploy
    show_summary
}

main "$@"
