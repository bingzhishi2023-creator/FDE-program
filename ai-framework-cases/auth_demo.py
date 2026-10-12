"""回环教学：签名凭证验证 + 服务端身份注册表 + 每次读取检查所有者。
自定义教学凭证不是 JWT/OIDC，也不是生产登录方案。issuer 是受信本地管理命令。
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ontology_demo import ROOT, load_model, validate

AUDIENCE = "qinghe-local-classroom"


def secret():
    key = os.environ.get("QINGHE_DEMO_SECRET", "")
    if len(key) < 32:
        raise ValueError("请先在受信本地终端设置至少 32 字符的 QINGHE_DEMO_SECRET")
    return key.encode()


def users():
    return {k: v for k, v in validate(load_model()).items() if v["type"] == "Employee"}


def encode(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def issue(user, key, ttl=300, now=None):
    if user not in users():
        raise ValueError("未知员工")
    payload = encode(json.dumps({"sub": user, "aud": AUDIENCE, "exp": int(time.time() if now is None else now) + ttl}, separators=(",", ":")).encode())
    return payload + "." + encode(hmac.digest(key, payload.encode(), "sha256"))


def verify(token, key, now=None):
    try:
        payload, signature = token.split(".")
        expected = encode(hmac.digest(key, payload.encode(), "sha256"))
        if not hmac.compare_digest(signature, expected):
            raise ValueError("签名不正确")
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        expiry = data.get("exp")
        if data.get("aud") != AUDIENCE or type(expiry) is not int or expiry <= (time.time() if now is None else now):
            raise ValueError("凭证已过期或用途不匹配")
        user = users().get(data.get("sub"))
        if not user:
            raise ValueError("员工已不存在")
        return user
    except (ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise ValueError("无效凭证") from exc


def read_claim(claim_id, user, db=ROOT / "operations.sqlite3"):
    if not re.fullmatch(r"R-\d{4}", claim_id):
        return 404, {"error": "not_found"}
    if not db.exists():
        return 503, {"error": "run_etl_first"}
    with closing(sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT claim_id, owner_id, status FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
    if not row:
        return 404, {"error": "not_found"}
    if user["role"] != "finance" and user["id"] != row["owner_id"]:
        return 403, {"error": "access_denied"}
    return 200, {"claim_id": row["claim_id"], "status": row["status"], "note": "虚构教学记录，只读"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            header = self.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                raise ValueError("缺少凭证")
            user = verify(header[7:], self.server.demo_key)
            if not self.path.startswith("/claims/"):
                status, data = 404, {"error": "not_found"}
            else:
                status, data = read_claim(self.path[len("/claims/"):], user)
        except ValueError:
            status, data = 401, {"error": "invalid_or_missing_credential"}
        except sqlite3.Error:
            status, data = 503, {"error": "data_unavailable"}
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass  # 教学服务不记录请求头或凭证。


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["issue", "serve"])
    parser.add_argument("--user", choices=["E001", "E002", "E003"], default="E001")
    parser.add_argument("--expired", action="store_true")
    args = parser.parse_args()
    try:
        key = secret()
        if args.command == "issue":
            print(issue(args.user, key, ttl=-1 if args.expired else 300))
        else:
            server = ThreadingHTTPServer(("127.0.0.1", 8003), Handler)
            server.demo_key = key
            print("教学 API：http://127.0.0.1:8003；另一受信终端签发凭证后查询。")
            server.serve_forever()
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc))
