"""Journal command: milestones."""
from scripts.commands.i18n import t


MILESTONE_DEFINITIONS = {
    "first_product_launch": {
        "keywords": ["launched", "shipped", "released", "live", "product launch", "上线", "发布"],
    },
    "first_customer": {
        "keywords": ["first customer", "first user", "first sale", "paid user", "got our first", "acquired first", "第一个客户"],
    },
    "revenue_milestone": {
        "keywords": ["$100", "$1k", "$10k", "mrr", "revenue", "first dollar", "收款", "收入"],
    },
    "mvp_complete": {
        "keywords": ["mvp done", "mvp complete", "prototype done", "mvp is", "prototype is", "done and ready", "MVP完成"],
    },
    "first_journal_entry": {
        "keywords": ["第一条", "第一个记录", "first entry", "开始了", "动笔", "第一步"],
    }
}


def run(customer_id: str, args: dict) -> dict:
    content = args.get("content", "")
    day = args.get("day", 1)
    detected = []
    content_lower = content.lower()

    for milestone_id, definition in MILESTONE_DEFINITIONS.items():
        for keyword in definition["keywords"]:
            if keyword in content_lower:
                detected.append({
                    "milestone_id": milestone_id,
                    "description": t(f"milestones.{milestone_id}", args),
                    "matched_keyword": keyword,
                    "day": day,
                    "confidence": 0.8
                })
                break

    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "day": day,
            "milestones_detected": detected,
            "count": len(detected)
        },
        "message": t("milestones.message", args, customer_id=customer_id, count=len(detected))
    }
