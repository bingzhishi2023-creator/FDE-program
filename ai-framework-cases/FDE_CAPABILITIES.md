# 青禾项目：业务语义、数据接入与身份权限

这些都是虚构本地教学资料。已安装 Python 即可运行，不另讲语言语法，不需要模型。与原有 `teaching-knowledge.sqlite3` 制度库分开；新的 `operations.sqlite3` 是单据库。

## 1. Ontology / 领域模型

先打开 `business-model.json`。Employee / Claim / Policy 是类型，E001 / R-0001 / P002 是实例，submitted_by / governed_by / handled_by 是明确含义的关系。

```powershell
py -3 ontology_demo.py validate
py -3 ontology_demo.py trace --employee E001
py -3 ontology_demo.py trace --employee E002
py -3 ontology_demo.py action --claim R-0001 --actor E003
py -3 ontology_demo.py action --claim R-0001 --actor E001
py -3 ontology_demo.py action --claim R-0002 --actor E003
```

校验结果：6 个对象。E001 关联 R-0001、差旅制度 v2 与处理人周敏；E002 关联 R-0002。动作预览允许财务从“材料审核中”请求补材料，拒绝员工角色及已经待补的状态，所有结果都不持久化。CLI 的 actor 是受信本地模拟，不是登录凭证。

这演示共同业务语言、约束校验和关系遍历，不是 OWL 推理器或 Palantir 平台。[Palantir 核心概念](https://www.palantir.com/docs/foundry/ontology/core-concepts/)、[W3C OWL 2 Primer](https://www.w3.org/TR/owl2-primer/) 可用于进一步区分产品与形式化语义。

## 2. ETL：来源 CSV → 数据质量 → 单据库

```powershell
py -3 etl_demo.py
Get-Content etl-report.json -Encoding UTF8
py -3 etl_demo.py
```

来源 `operations/raw-claims.csv` 有 5 行。对齐员工编号、状态和金额后，2 行有效数据入库；未知员工、负金额、未知状态各一行拒收。来源行号和文件 SHA-256 保存在库与报告中，便于追溯。第二次导入总记录仍为 2：以单据号 upsert，不造重复单。来源消失的记录不自动删除，增量、删除、历史和并发策略在真实项目另行设计。

## 3. 验证身份，再检查对象权限

自定义 HMAC 教学凭证有效期 5 分钟；不是 JWT、OIDC、SSO 或生产登录。签发终端是受信本地管理环境，真实用户不能持有密钥。角色从服务器的员工表读取；服务只监听 127.0.0.1。确认端口 8003 未占用，在本案例根目录的同一个 PowerShell 执行：

```powershell
py -3 etl_demo.py
$python = py -3 -c "import sys; print(sys.executable)"
$env:QINGHE_DEMO_SECRET = py -3 -c "import secrets; print(secrets.token_urlsafe(32))"
$linToken = py -3 auth_demo.py issue --user E001
$financeToken = py -3 auth_demo.py issue --user E003
$expiredToken = py -3 auth_demo.py issue --user E001 --expired
$apiProcess = Start-Process -FilePath $python -ArgumentList @('auth_demo.py','serve') -WorkingDirectory (Get-Location).Path -WindowStyle Hidden -PassThru
```

待服务启动后发送请求：

```powershell
Invoke-RestMethod http://127.0.0.1:8003/claims/R-0001 -Headers @{Authorization="Bearer $linToken"}
Invoke-RestMethod http://127.0.0.1:8003/claims/R-0002 -Headers @{Authorization="Bearer $linToken"}
Invoke-RestMethod http://127.0.0.1:8003/claims/R-0002 -Headers @{Authorization="Bearer $financeToken"}
Invoke-RestMethod http://127.0.0.1:8003/claims/R-0001 -Headers @{Authorization="Bearer $expiredToken"}
```

结果依次为 200（材料审核中）、403（无权读他人单据）、200（等待补充行程单）、401（失效凭证）。PowerShell 会把 4xx 显示为错误响应；这是服务的拒绝结果。如果超过 5 分钟，重新签发。停止本次启动的进程，并清理本终端变量：

```powershell
Stop-Process -Id $apiProcess.Id
Remove-Item Env:QINGHE_DEMO_SECRET
Remove-Variable linToken,financeToken,expiredToken
```

真实交付应接企业身份提供方、成熟认证库及 HTTPS，补充会话与撤销、审计、租户边界等。[OWASP 授权说明](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)、[OpenID Connect 说明](https://openid.net/developers/how-connect-works/)。本章没有自动给另外三个框架案例或 AI 包加上认证：整合时须把验证后的身份落实到每条读取路径。
