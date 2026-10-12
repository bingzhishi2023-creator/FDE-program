# 青禾报销助手：工程基础贯穿项目

青禾是虚构公司，制度也是教学资料。员工小林问“报销需要哪些材料？”，答案要显示当前有效的原文来源。财务同事周敏可以多看一份预算资料；行政管理员维护制度。

项目不是自动报销、审批或自主智能体。当前小型资料问答按有效性与部门过滤，把可见资料作为上下文；没有语义检索。后面的独立 RAG 项目再演示 Embedding 与检索。

## 1. 网页把问题送到后端：HTTP / API / JSON

在本目录运行（无需第三方库）：

```powershell
py -3 http_demo.py
```

打开 http://127.0.0.1:8002/project，发送预填的问题。页面显示请求 `POST /inspect`、请求头、question JSON 和响应。正常返回 HTTP 200、received、model_called=false；空问题返回 400。第一阶段只收发，不调用模型。停止服务用 Ctrl+C。

## 2. 三份资料入库：清洗 / SQLite / SQL / 权限

```powershell
py -3 data_demo.py init
py -3 data_demo.py query --as-user employee
py -3 data_demo.py query --as-user finance
```

sample-documents.csv 有三份资料。程序去掉首尾空格并验证字段，写入本目录 teaching-knowledge.sqlite3。员工只看到 public-travel（发票与行程单）；财务看到 public-travel 与 finance-budget；停用旧版 old-travel 始终排除。

```powershell
py -3 data_demo.py retire --id public-travel
py -3 data_demo.py query --as-user employee
py -3 data_demo.py init
```

撤回后员工 sources 为空；init 恢复教学数据，只操作本项目 documents 表。

## 3. 准备真实模型问答

需要 Python 3.11+ 和官方 Ollama 应用，保持 Ollama 运行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen3:4b
py -3 data_demo.py init
```

代码采用 qwen3 的 think=false，模型首次加载可能较慢。模型调用超时 90 秒，生成内容与引用要核对原文。课程验证真实框架、真实数据库和错误处理，模型调用在自动检查中被替身隔离，没有下载模型做真实推理。

## 4. Flask 版本：把入口、资料和模型串起来

```powershell
$env:DEMO_USER = "employee"
.\.venv\Scripts\python.exe -m flask --app project_flask run --port 5000
```

打开 http://127.0.0.1:5000/project，发送同一个问题。预期：HTTP 200、模型 answer、public-travel 来源，来源原文为“报销需提交发票与行程单。”答案非固定模板。

http://127.0.0.1:5000/sources 可直接查看资料，无需模型。另一个终端撤回 public-travel 后再问，应返回 409，不调用模型。恢复 init 后再问。

```powershell
$body = @{question="报销需要哪些材料？"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:5000/ask-policy" `
  -Method Post -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

## 5. FastAPI 版本：同一业务加上接口契约

```powershell
$env:DEMO_USER = "employee"
.\.venv\Scripts\python.exe -m uvicorn project_fastapi:app --reload --port 8000
```

打开 http://127.0.0.1:8000/project 或 http://127.0.0.1:8000/docs。在 POST /ask-policy 发送 `{"question":"报销需要哪些材料？"}`，应返回 answer、sources、simulated_identity 和 note。它使用与 Flask 相同的数据库、业务与模型客户端。

空问题、错误类型或额外 department 字段返回 422。Flask 同类输入返回 400；二者都拒绝用户自报部门。撤回资料后 409；模型故障 502；数据库或教学身份配置异常 503。

Ctrl+C 后在同一终端设置 `$env:DEMO_USER = "finance"` 再启动。/sources 应增加 finance-budget，仍没有 old-travel。**DEMO_USER 是启动配置中的教学身份，不是员工登录认证**；本机项目不允许前端任意指定它。环境变量设置与服务启动要在同一终端。

## 6. Django 后台版本：让行政用网页维护

安装依赖与模型后：

```powershell
cd django_portal
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py seed_project
..\.venv\Scripts\python.exe manage.py createsuperuser
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

seed_project 从同一 CSV 导入或更新两份全员公开资料；财务内部资料不导入。它保存到 Django 独立数据库，不和前面的数据库自动同步。再次执行 seed_project 会把这两条公开教学记录恢复到 CSV 状态。

用自己设置的管理员账号登录 http://127.0.0.1:8001/admin/，文档中应有有效公开制度和停用旧版。访问 http://127.0.0.1:8001/demo/ 问同一个问题；来源不含旧版。后台取消公开制度 active 后，问答返回 409。重新勾选恢复。

此版本问答仅供 staff 管理员验证，不是员工门户。没有实现逐部门文档权限；生产开放给员工前必须补角色与访问过滤、发布/索引同步。少量资料最多取 5 份、每份 1800 字符；不具备语义检索。

## 概念与实际文件对照

| 概念 | 项目文件与操作 |
| --- | --- |
| 前端、请求与响应 | project_ui.html 的表单、fetch 与结果区 |
| HTTP / API / JSON | http_demo.py 的 /inspect、/health 与 JSON 回执 |
| 数据清洗与元数据 | sample-documents.csv、data_demo.py init |
| SQL 与权限过滤 | data_demo.visible_documents 的参数化 WHERE |
| 业务层 | policy_service.py：资料、上下文与问答结果 |
| Flask 路由与手动校验 | project_flask.py /ask-policy |
| FastAPI 契约与异步 | project_fastapi.py Question、Answer、/docs |
| Django ORM、迁移与 Admin | django_portal/knowledge 的模型、视图、管理页 |

## 常见问题

- 页面打不开：确认相应服务终端正在运行、地址端口正确。项目网页要通过上述 HTTP 地址打开，不要直接双击 HTML。
- 409：尚未初始化数据库，或员工没有有效可见资料。先 init；用 /sources 看集合。
- 502：确认 Ollama 在运行并且 CHAT_MODEL 指定的模型已安装。默认 qwen3:4b。
- 503：检查数据库是否可读、DEMO_USER 是否是 employee 或 finance。
- 400 / 422：只发送合法 question。不要在请求里指定部门或角色。
- Django 未登录会转到登录页。使用 /demo/ 的表单保留 CSRF；不要关闭保护来联调。

这些是本机开发服务，绑定环回地址。没有生产员工认证；不要把教学服务直接暴露到公网。真实交付还要锁定依赖、HTTPS、独立密钥、身份权限、并发限制、日志与数据维护机制。旧的 flask_app.py、fastapi_app.py 是附带的最小模型调用参考；主项目使用带 project_ 前缀的文件。
