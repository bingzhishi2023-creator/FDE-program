"""报销助手的共享业务层：SQLite 来源过滤与模型调用。"""
from contextlib import closing
import os
import sqlite3
from ai_client import answer_sync, answer_async
from data_demo import DATABASE, visible_documents


class ProjectDataError(Exception):
    def __init__(self, message, status=409):
        self.status = status
        super().__init__(message)


def project_sources():
    # 本机教学身份来自服务启动配置，不读取请求中自报的部门。
    identity = os.getenv("DEMO_USER", "employee")
    department = {"employee": "sales", "finance": "finance"}.get(identity)
    if department is None:
        raise ProjectDataError("DEMO_USER 只能设置为 employee 或 finance", 503)
    if not DATABASE.exists():
        raise ProjectDataError("先在案例根目录运行 data_demo.py init")
    try:
        with closing(sqlite3.connect(f"{DATABASE.as_uri()}?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            records = visible_documents(db, department)
    except sqlite3.Error as exc:
        raise ProjectDataError("教学数据库无法读取，请检查初始化状态", 503) from exc
    return identity, [dict(id=f"S{i+1}", document_id=row["id"], title=row["title"], text=row["text"])
                      for i, row in enumerate(records)]


def prepared_context():
    identity, sources = project_sources()
    if not sources:
        raise ProjectDataError("没有有效且可见的资料，暂不能生成制度答案")
    context = "\n\n".join(f"[{s['id']}] {s['title']}\n{s['text']}" for s in sources)
    return identity, sources, context


def result(answer, identity, sources):
    return {"answer": answer, "sources": sources, "simulated_identity": identity,
            "note": "三份教学资料按有效性与部门筛选后作为上下文；无语义检索，引用与答案需核对"}


def ask_policy_sync(question):
    identity, sources, context = prepared_context()
    return result(answer_sync(question, context=context), identity, sources)


async def ask_policy_async(question):
    identity, sources, context = prepared_context()
    return result(await answer_async(question, context=context), identity, sources)
