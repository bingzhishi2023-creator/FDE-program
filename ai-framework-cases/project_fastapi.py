from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ai_client import ModelServiceError
from policy_service import ProjectDataError, ask_policy_async, project_sources

app = FastAPI(title="青禾报销助手 · 教学项目")


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def clean(cls, value):
        if not value.strip():
            raise ValueError("问题不能为空白")
        return value.strip()


class Source(BaseModel):
    id: str
    document_id: str
    title: str
    text: str


class Answer(BaseModel):
    answer: str
    sources: list[Source]
    simulated_identity: str
    note: str


@app.get("/project", response_class=FileResponse)
def project():
    return FileResponse(Path(__file__).with_name("project_ui.html"))


@app.get("/sources")
def sources():
    try:
        identity, records = project_sources()
        return {"simulated_identity": identity, "sources": records}
    except ProjectDataError as exc:
        raise HTTPException(exc.status, str(exc)) from exc


@app.post("/ask-policy", response_model=Answer)
async def ask(data: Question):
    try:
        return await ask_policy_async(data.question)
    except ProjectDataError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    except ModelServiceError as exc:
        raise HTTPException(502, "模型服务暂不可用，请检查 Ollama") from exc
