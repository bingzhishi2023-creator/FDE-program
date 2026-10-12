"""虚构 CSV → 统一业务含义 → 本地 SQLite，记录拒收原因与来源。"""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ontology_demo import ROOT, load_model, validate

STATUS_MAP = {"审核中": "材料审核中", "待补材料": "等待补充行程单", "完成": "已完成"}


def import_claims(source=ROOT / "operations" / "raw-claims.csv", db=ROOT / "operations.sqlite3"):
    model = load_model()
    registry = validate(model)
    checksum = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    accepted, rejected, seen = [], [], set()
    with Path(source).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for number, raw in enumerate(rows, 2):
        row = {key: value.strip() for key, value in raw.items() if key is not None and value is not None}
        try:
            claim_id, employee_id = row["单据号"], row["员工编号"]
            if not re.fullmatch(r"R-\d{4}", claim_id) or claim_id in seen:
                raise ValueError("单据编号格式错误或本批重复")
            seen.add(claim_id)
            if registry.get(employee_id, {}).get("type") != "Employee":
                raise ValueError("员工编号不在权威员工表中")
            amount = Decimal(row["报销金额"])
            if not amount.is_finite() or amount < 0 or amount != amount.quantize(Decimal("0.01")):
                raise ValueError("金额须非负且最多两位小数")
            status = STATUS_MAP.get(row["流程状态"])
            if not status:
                raise ValueError("状态没有映射规则，需业务负责人确认")
            accepted.append((claim_id, employee_id, str(amount.quantize(Decimal("0.01"))), status, "P002", "E003", row["来源行"], number, checksum))
        except (ValueError, InvalidOperation, KeyError) as exc:
            rejected.append({"line": number, "source_row": row.get("来源行"), "reason": str(exc)})
    with closing(sqlite3.connect(db)) as conn:
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS claims (claim_id TEXT PRIMARY KEY, owner_id TEXT, amount TEXT, status TEXT, policy_id TEXT, handler_id TEXT, source_row TEXT, source_line INTEGER, source_sha256 TEXT)")
            conn.executemany("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(claim_id) DO UPDATE SET owner_id=excluded.owner_id,amount=excluded.amount,status=excluded.status,policy_id=excluded.policy_id,handler_id=excluded.handler_id,source_row=excluded.source_row,source_line=excluded.source_line,source_sha256=excluded.source_sha256", accepted)
        count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    return {"source": Path(source).name, "source_sha256": checksum, "accepted": len(accepted), "rejected": rejected, "database_rows": count, "mode": "按单据号 upsert；拒收行不入库；不自动删除来源里消失的旧记录"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "operations" / "raw-claims.csv")
    args = parser.parse_args()
    try:
        report = import_claims(args.source)
        (ROOT / "etl-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise SystemExit("接入失败：" + str(exc))
