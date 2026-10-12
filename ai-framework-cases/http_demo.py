"""本机 HTTP / API / JSON 案例：观察请求与响应，不调用模型。"""
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/project":
            data = Path(__file__).with_name("project_ui.html").read_text(encoding="utf-8").replace("const route='/ask-policy'", "const route='/inspect'").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/health":
            self.reply(200, {"status": "ok"})
        else:
            self.reply(404, {"error": "接口不存在"})

    def do_POST(self):
        if self.path != "/inspect":
            self.reply(404, {"error": "接口不存在"})
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            self.reply(415, {"error": "请使用 application/json"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 8192:
                self.reply(413, {"error": "请求体应为 1–8192 字节"})
                return
            body = json.loads(self.rfile.read(size).decode("utf-8"))
        except (ValueError, UnicodeError):
            self.reply(400, {"error": "JSON 格式不正确"})
            return
        if not isinstance(body, dict):
            self.reply(400, {"error": "请求体必须是 JSON 对象"})
            return
        question = body.get("question")
        if not isinstance(question, str) or not question.strip() or len(question) > 500:
            self.reply(400, {"error": "question 必须为 1–500 字符的非空文字"})
            return
        self.reply(200, {"received": question.strip(), "next_step": "交给检索或智能体运行器", "model_called": False})


if __name__ == "__main__":
    print("HTTP 案例：http://127.0.0.1:8002；Ctrl+C 停止")
    ThreadingHTTPServer(("127.0.0.1", 8002), Handler).serve_forever()
