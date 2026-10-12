from flask import Flask, jsonify, request
from ai_client import ModelServiceError, answer_sync

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10_000


@app.get("/health")
def health():
    return jsonify(status="ok", framework="Flask")


@app.post("/ask")
def ask():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="请提交 JSON 对象"), 400
    question = data.get("question")
    if not isinstance(question, str) or not question.strip():
        return jsonify(error="question 必须是非空文字"), 400
    if len(question) > 500:
        return jsonify(error="问题最多 500 字符"), 400
    try:
        return jsonify(answer=answer_sync(question.strip()))
    except ModelServiceError:
        return jsonify(error="模型服务暂不可用，请检查 Ollama 和模型安装状态"), 502


# python -m flask --app flask_app run --port 5000
# 开发服务；无认证，不要直接公开。
