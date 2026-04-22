"""
OPC200 Alertmanager → 飞书 Bot 转换服务
接收 Alertmanager webhook，格式化成飞书消息卡片发送
"""

import json
import logging
import os
import sys
import time
from datetime import datetime

import requests
from flask import Flask, request, jsonify

# ========== 配置 ==========
APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a962ca103ffa1cd1")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
CHAT_ID = os.environ.get("FEISHU_CHAT_ID", "")  # 群 ID，启动后配置

TOKEN_CACHE = {"token": "", "expires_at": 0}

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ========== 飞书 Token ==========
def get_tenant_access_token() -> str:
    now = time.time()
    if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"] - 60:
        return TOKEN_CACHE["token"]

    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        logger.error("获取 token 失败: %s", data)
        raise RuntimeError(f"Feishu token error: {data}")

    token = data["tenant_access_token"]
    expire = data.get("expire", 7200)
    TOKEN_CACHE["token"] = token
    TOKEN_CACHE["expires_at"] = now + expire
    return token


# ========== 格式化告警卡片 ==========
def build_card(alerts: list) -> dict:
    elements = []
    critical_count = 0
    warning_count = 0

    for alert in alerts[:5]:  # 最多显示 5 条
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        status = alert.get("status", "firing")
        severity = labels.get("severity", "unknown")
        alertname = labels.get("alertname", "Unknown")
        summary = annotations.get("summary", "")
        description = annotations.get("description", "")
        job = labels.get("job", "")

        color = "red" if severity == "critical" else "orange" if severity == "warning" else "blue"
        emoji = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🔵"
        resolved = "✅ 已恢复" if status == "resolved" else "🔔 告警中"

        if severity == "critical":
            critical_count += 1
        elif severity == "warning":
            warning_count += 1

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"{emoji} **{alertname}** | `{severity.upper()}` | {resolved}\n"
                           f"📌 {summary}\n"
                           f"📝 {description}\n"
                           f"🏷️ job: {job}"
            }
        })
        elements.append({"tag": "hr"})

    # 去掉最后一个 hr
    if elements and elements[-1]["tag"] == "hr":
        elements.pop()

    header_title = f"OPC200 告警 ({critical_count} P0 / {warning_count} P1)"
    template = "red" if critical_count > 0 else "orange" if warning_count > 0 else "blue"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": header_title},
            "template": template,
        },
        "elements": elements,
    }


# ========== 发送飞书消息 ==========
def send_feishu_message(card: dict) -> bool:
    if not CHAT_ID:
        logger.error("FEISHU_CHAT_ID 未配置，无法发送消息")
        return False

    try:
        token = get_tenant_access_token()
    except Exception as e:
        logger.error("获取 token 失败: %s", e)
        return False

    content = json.dumps({"config": card["config"], "header": card["header"], "elements": card["elements"]})
    payload = {
        "receive_id": CHAT_ID,
        "msg_type": "interactive",
        "content": content,
    }

    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        logger.error("发送飞书消息失败: %s", data)
        return False

    logger.info("飞书消息发送成功, message_id=%s", data.get("data", {}).get("message_id", "?"))
    return True


# ========== HTTP 路由 ==========
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "chat_id_configured": bool(CHAT_ID)})


@app.route("/webhook/feishu", methods=["POST"])
def webhook_feishu():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    alerts = data.get("alerts", [])
    if not alerts:
        return jsonify({"status": "no alerts"}), 200

    logger.info("收到 %d 条告警", len(alerts))
    card = build_card(alerts)
    ok = send_feishu_message(card)
    return jsonify({"status": "sent" if ok else "failed"}), 200 if ok else 500


@app.route("/config/chat_id", methods=["POST"])
def set_chat_id():
    """动态配置 Chat ID，不用重启服务"""
    global CHAT_ID
    data = request.get_json(force=True)
    chat_id = data.get("chat_id", "")
    if not chat_id:
        return jsonify({"error": "chat_id required"}), 400
    CHAT_ID = chat_id
    os.environ["FEISHU_CHAT_ID"] = chat_id
    logger.info("Chat ID 已更新: %s", chat_id)
    return jsonify({"status": "ok", "chat_id": chat_id})


@app.route("/test", methods=["POST"])
def test_send():
    """手动测试发送一条消息"""
    test_card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "OPC200 飞书告警测试"},
            "template": "green",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "✅ 转换服务运行正常\n🕐 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        ],
    }
    ok = send_feishu_message(test_card)
    return jsonify({"status": "sent" if ok else "failed"}), 200 if ok else 500


# ========== 启动 ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    logger.info("OPC200 Feishu Alert Adapter starting on port %d", port)
    logger.info("App ID: %s", APP_ID)
    logger.info("Chat ID configured: %s", bool(CHAT_ID))
    app.run(host="0.0.0.0", port=port, debug=False)
