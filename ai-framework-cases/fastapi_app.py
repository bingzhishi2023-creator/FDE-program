from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ai_client import ModelServiceError, answer_async

app = FastAPI(title="FastAPI AI 问答案例")


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def clean(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("问题不能为空白")
        return value.strip()


class AskResponse(BaseModel):
    answer: str


@app.get("/health")
def health():
    return {"status": "ok", "framework": "FastAPI"}


@app.post("/ask", response_model=AskResponse)
async def ask(data: AskRequest):
    try:
        return AskResponse(answer=await answer_async(data.question))
    except ModelServiceError as exc:
        raise HTTPException(502, "模型服务暂不可用，请检查 Ollama 和模型安装状态") from exc


# python -m uvicorn fastapi_app:app --reload --port 8000
