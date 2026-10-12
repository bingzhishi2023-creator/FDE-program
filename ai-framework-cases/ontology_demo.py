"""业务语义模型与关系遍历教学；不是 OWL 推理器或 Palantir 运行时。"""
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_model(path=ROOT / "business-model.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(model):
    objects = {o["id"]: o for o in model["objects"]}
    if len(objects) != len(model["objects"]):
        raise ValueError("对象 ID 重复")
    for obj in objects.values():
        spec = model["types"].get(obj["type"])
        if not spec or any(key not in obj for key in spec["required"]):
            raise ValueError("对象类型或必填属性不正确")
        if obj["type"] == "Claim":
            try:
                amount = Decimal(obj["amount"])
                if not amount.is_finite() or amount < 0 or obj["status"] not in spec["statuses"]:
                    raise ValueError("金额或状态不正确")
            except InvalidOperation as exc:
                raise ValueError("金额不是数字") from exc
    for link in model["links"]:
        spec = model["link_types"].get(link["type"])
        source, target = objects.get(link["from"]), objects.get(link["to"])
        if not spec or not source or not target or source["type"] != spec["from"] or target["type"] != spec["to"]:
            raise ValueError("关系端点或类型不正确")
    for obj in objects.values():
        if obj["type"] == "Claim":
            for kind in ("submitted_by", "governed_by", "handled_by"):
                links = [l for l in model["links"] if l["from"] == obj["id"] and l["type"] == kind]
                if len(links) != 1:
                    raise ValueError("每张单据须有且仅有一个提交人、适用制度及处理人")
            policy = next(l["to"] for l in model["links"] if l["from"] == obj["id"] and l["type"] == "governed_by")
            if objects[policy]["active"] is not True:
                raise ValueError("单据关联了无效制度")
    return objects


def trace(model, employee_id):
    objects = validate(model)
    if employee_id not in objects or objects[employee_id]["type"] != "Employee":
        raise ValueError("员工不存在")
    claims = []
    for link in model["links"]:
        if link["type"] == "submitted_by" and link["to"] == employee_id:
            claim = objects[link["from"]]
            related = {l["type"]: objects[l["to"]] for l in model["links"] if l["from"] == claim["id"]}
            claims.append({"claim": claim, "policy": related["governed_by"], "handler": related["handled_by"]})
    return {"employee": objects[employee_id]["name"], "claims": claims, "note": "关系遍历；身份与访问校验由后续授权章实现"}


def preview_action(model, claim_id, actor_id):
    objects = validate(model)
    actor, claim = objects.get(actor_id), objects.get(claim_id)
    rule = model["actions"]["request_materials"]
    allowed = bool(actor and claim and actor["type"] == "Employee" and actor["role"] == rule["allowed_role"] and claim["type"] == rule["target_type"] and claim["status"] == rule["from_status"])
    return {"allowed": allowed, "before": claim.get("status") if claim else None, "proposed_after": rule["to_status"] if allowed else None, "persisted": False, "note": "受信本地调用者模拟；只预览规则，不修改或审批单据"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["validate", "trace", "action"])
    parser.add_argument("--employee", default="E001")
    parser.add_argument("--claim", default="R-0001")
    parser.add_argument("--actor", default="E003")
    args = parser.parse_args()
    try:
        model = load_model()
        result = {"valid": True, "object_count": len(validate(model))} if args.command == "validate" else trace(model, args.employee) if args.command == "trace" else preview_action(model, args.claim, args.actor)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit("模型校验失败：" + str(exc))
