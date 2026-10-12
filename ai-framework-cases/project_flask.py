from pathlib import Path
from flask import Flask, jsonify, request, send_file
from ai_client import ModelServiceError
from policy_service import ProjectDataError, ask_policy_sync, project_sources

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10_000


@app.get("/project")
def project():
    return send_file(Path(__file__).with_name("project_ui.html"))


@app.get("/sources")
def sources():
    try:
        identity, records = project_sources()
        return jsonify(simulated_identity=identity, sources=records)
    except ProjectDataError as exc:
        return jsonify(error=str(exc)), exc.status


@app.post("/ask-policy")
def ask():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"question"}:
        return jsonify(error="仅提交 question 字段；身份由服务端教学配置决定"), 400
    question = data["question"]
    if not isinstance(question, str) or not question.strip() or len(question) > 500:
        return jsonify(error="问题须为 1–500 字符的非空文字"), 400
    try:
        return jsonify(ask_policy_sync(question.strip()))
    except ProjectDataError as exc:
        return jsonify(error=str(exc)), exc.status
    except ModelServiceError:
        return jsonify(error="模型服务暂不可用，请检查 Ollama"), 502
