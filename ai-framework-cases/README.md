主项目请先阅读 [PROJECT.md](PROJECT.md)：青禾报销助手分六步串起通信、资料和框架；下文保留最小接口参考案例。

新增 FDE 能力见 [FDE_CAPABILITIES.md](FDE_CAPABILITIES.md)：业务对象模型、ETL 单据接入与质量、身份认证及逐对象授权。它们沿用青禾人物与编号，提供标准库即可运行的完整命令。

# 工程基础与 Flask / FastAPI / Django · AI 上手案例

三个案例调用同一个真实 Ollama 模型客户端，用来对照框架的入口和业务组织。需要 Python 3.11+ 与官方 Ollama 应用。源码不带模型文件；课程制作时验证了框架接口和错误处理，没有下载模型做真实推理。

学习顺序：HTTP / API / JSON → 数据清洗 / SQL / 权限 → 框架选型 → Flask → FastAPI → Django。三个框架是并列选择，顺序只是从最小接口到标准服务再到管理平台的教学递进；它们之间没有运行依赖。

## 先运行通信案例（不需要第三方库或模型）

在案例根目录运行 `py -3 http_demo.py`，保持终端开启。另一个 PowerShell：

```powershell
Invoke-RestMethod http://127.0.0.1:8002/health
$body = @{question="报销需要哪些材料？"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8002/inspect" `
  -Method Post -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

预期：health 返回 status=ok；inspect 返回 received、next_step、model_called=false。HTTP 像递送规则，API 像办事窗口，JSON 像结构化表单。此服务只收发和校验，不调用 AI。空 question 返回 400；错误地址返回 404；格式不是 application/json 返回 415。Ctrl+C 停止。它可作为理解模型服务与智能体工具接口的第一步，真实工具执行逻辑需另接。

## 再运行数据案例（不需要第三方库或模型）

```powershell
py -3 data_demo.py init
py -3 data_demo.py query --as-user employee
py -3 data_demo.py query --as-user finance
py -3 data_demo.py retire --id public-travel
py -3 data_demo.py query --as-user employee
# 恢复案例数据
py -3 data_demo.py init
```

数据来源 sample-documents.csv，存入本机 teaching-knowledge.sqlite3。init 会重建本案例 documents 表的内容，不连接企业数据。先清理字段首尾空格并检查有效状态，再参数化写入和查询。初次导入返回 imported=3；employee 只看到 public-travel；finance 看到 public-travel 与 finance-budget；所有身份都看不到已停用的 old-travel。停用 public-travel 后 employee 的 sources 为空。

`--as-user` 是模拟身份的教学开关，不是真实登录认证。生产系统的身份必须由验证后的会话或令牌确定，不接受用户自由指定部门。SQL 在资料交给模型前筛选有效性和可见性；向量检索可在这份允许访问的候选集合中执行。这个案例没有模型推理或 Embedding。

## 准备（在案例根目录）

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen3:4b
```

确认 Ollama 已运行；其默认模型服务地址为 http://127.0.0.1:11434。官方说明：https://docs.ollama.com/quickstart 。模型首次加载可能较慢，实际资源需求取决于模型和硬件。

## Flask：最小模型问答接口

场景：给已有的轻量内部工具添加 AI 问答入口。框架负责路由和响应，ai_client.py 调模型；若要多步工具执行，需要另接 harness。

```powershell
.\.venv\Scripts\python.exe -m flask --app flask_app run --port 5000
```

另开 PowerShell：

```powershell
$body = @{question="用一句话解释 RAG"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:5000/ask" `
  -Method Post -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

输出 answer 来自本机模型。输入不合法返回 400，模型服务失败返回 502。此处没有企业资料，不能把通用模型回答当企业事实。

## Django：资料管理后台 + 有来源的模型问答

场景：知识助手需要管理员维护制度、停用旧版、登录后台。Django 的 Model 是数据库记录结构，Admin 是管理界面；智能体使用的资料仍要按权限筛选。

```powershell
cd django_portal
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py createsuperuser
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

1. 打开 http://127.0.0.1:8001/admin/，用自己创建的管理员登录。
2. 在“教学知识库 / 文档”添加标题“差旅制度”，正文“报销需提交发票与行程单”，勾选“当前有效”。
3. 打开 http://127.0.0.1:8001/demo/，输入“报销需要哪些材料？”。表单保留 CSRF 校验，页面返回答案和来源。
4. 在 Admin 停用文档后再请求。若没有其他有效文档，返回 409；不会读取停用文档。

Model 是数据库结构，不是大语言模型。Admin 管理后台、账号会话和 ORM 由 Django 提供，ai_client.py 负责生成。示例最多取 5 份有效资料、每份前 1800 字符，并按固定 ID 顺序排列；它不是语义检索或完整 RAG，资料多时可能漏掉相关内容。它也没有逐用户文档权限，仅允许登录管理员查看。真实项目应增加访问过滤、发布版本与索引同步。

## FastAPI：自动校验与文档的异步 AI 接口

场景：同一 AI 能力需要供网页、聊天机器人和其他系统调用。自动接口文档和输入校验方便协作。框架提供服务入口，RAG、工具与智能体执行循环由应用另外接入。

回到案例根目录：

```powershell
.\.venv\Scripts\python.exe -m uvicorn fastapi_app:app --reload --port 8000
```

打开 http://127.0.0.1:8000/docs，在 POST /ask 发送 `{"question":"用一句话解释 RAG"}`。合法问题调用真实模型；空问题、全空白问题或类型不合法返回 422。模型服务失败返回 502。异步 HTTP 能在等待网络期间安排其他 I/O，不会直接加速模型推理。

完整 RAG 示例在另一下载包 fde-rag-starter.zip。先关闭本例占用 8000 端口的服务，再运行该项目并建立索引。

## 公用模型配置与边界

可在启动前设置 `$env:OLLAMA_URL` 和 `$env:CHAT_MODEL`。qwen3 示例使用 think=false，换模型需确认其支持。模型调用超时 90 秒，无自动重试。答案和来源需要人工核对，文本 Prompt 不能独立防止提示注入。

以上都是本机开发案例。Flask / FastAPI 例子无认证；Django 的公开开发用 SECRET_KEY 与 DEBUG 只适合本机示例。生产使用独立服务端密钥、关闭 DEBUG、部署 HTTPS、身份权限、并发限制和监控。不要把开发服务直接暴露到公网。依赖范围用于教学，生产需锁定经验证版本。
