"""CSV 清洗 → SQLite → 权限过滤；教学身份由 CLI 固定模拟，不是认证。"""
from contextlib import closing
import argparse
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "teaching-knowledge.sqlite3"


def load(db):
    db.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, title TEXT NOT NULL, department TEXT NOT NULL, active INTEGER NOT NULL, text TEXT NOT NULL)")
    # 初始化仅重建本案例的 documents 表内容。
    db.execute("DELETE FROM documents")
    with (ROOT / "sample-documents.csv").open(encoding="utf-8-sig", newline="") as file:
        for raw in csv.DictReader(file):
            row = {key: value.strip() for key, value in raw.items()}
            if row["active"] not in {"0", "1"} or any(not row[key] for key in ("id", "title", "department", "text")):
                raise ValueError("文档缺少元数据或有效状态错误")
            db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?)", (row["id"], row["title"], row["department"], int(row["active"]), row["text"]))


def visible_documents(db, trusted_department):
    return [dict(row) for row in db.execute(
        "SELECT id, title, department, text FROM documents WHERE active = ? AND (department = ? OR department = ?) ORDER BY id",
        (1, "all", trusted_department),
    )]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "query", "retire"])
    parser.add_argument("--as-user", choices=["employee", "finance"], default="employee", help="模拟已经过服务端验证的身份")
    parser.add_argument("--id", default="public-travel", help="retire 的文档编号")
    args = parser.parse_args()
    if args.command != "init" and not DATABASE.exists():
        parser.error("请先运行 data_demo.py init")
    with closing(sqlite3.connect(DATABASE)) as db, db:
        db.row_factory = sqlite3.Row
        if args.command == "init":
            load(db)
            result = {"imported": db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]}
        elif args.command == "retire":
            cursor = db.execute("UPDATE documents SET active = ? WHERE id = ?", (0, args.id))
            result = {"retired": cursor.rowcount}
        else:
            trusted_department = {"employee": "sales", "finance": "finance"}[args.as_user]
            result = {"simulated_identity": args.as_user, "sources": visible_documents(db, trusted_department)}
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
