# 栈桥 · SaaS 支持台

面向 B2B SaaS 场景的智能客服工作台。Vue 3 提供聊天、知识管理、运行详情和质量评测页面；Python / FastAPI 后端通过 LangChain 调用 DeepSeek 或其他兼容 Chat Completions 的模型。

支持通用咨询、技术支持、账单咨询与人工交接摘要，包含多路意图识别、多 Agent 路由、RAG、MCP、动态 Skills、会话记忆和回归评测。

## 快速启动

完整服务推荐 Docker Desktop / Docker Engine + Compose v2。第一次构建会下载 Python 依赖和 Embedding 模型，需要能够访问软件源与镜像仓库。

```powershell
git clone https://github.com/fkfk912912/SaaS.git
cd SaaS
Copy-Item SaaSBackend/.env.example SaaSBackend/.env
# 编辑 SaaSBackend/.env，填写 OPENAI_API_KEY 和账号可用的模型 ID
.\Start-SaaS.ps1
```

Linux / macOS 可使用同一套 Compose：

```sh
cp SaaSBackend/.env.example SaaSBackend/.env
# 编辑配置后启动
docker compose --env-file SaaSBackend/.env up -d --build
```

最少需要配置：

```dotenv
OPENAI_API_KEY=填写自己的模型密钥
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=填写账号实际可用的模型ID
DEEPSEEK_THINKING=disabled
```

完整配置模板在 [SaaSBackend/.env.example](SaaSBackend/.env.example)。模型名称与权限以服务商账号为准。

| 地址 | 用途 |
| --- | --- |
| http://localhost:5175 | 支持工作台 |
| http://localhost:8010/docs | API 文档 |
| http://localhost:8010/health | 健康检查 |
| http://localhost:9091 | Prometheus |

停止：`.\Stop-SaaS.ps1`，或 `docker compose --env-file SaaSBackend/.env down`。停止命令保留会话、知识库和监控数据卷。

## 目录

```text
SaaS/
├── SaaSBackend/          Python 后端、测试、Skills 与配置
├── SaaSFrontend/         Vue 前端、测试与 Nginx 配置
├── docs/                 使用、开发、架构与代码阅读说明
├── compose.yaml          完整服务的统一部署入口
├── Start-SaaS.ps1        Windows 启动
└── Stop-SaaS.ps1         停止服务
```

本机 `.env`、虚拟环境、数据库、依赖目录和历史验证资料由 `.gitignore` 排除；新使用者通过模板和安装命令创建自己的环境。

## 功能与边界

| 模块 | 作用 |
| --- | --- |
| 意图与路由 | LLM / Embedding / Pattern 融合，主辅 Agent 协作与失败回退 |
| 知识与工具 | 查询改写、并行召回、去重重排、角色工具白名单、JSON Schema 校验 |
| 记忆与可靠性 | Redis 工作记忆、Chroma 长期记忆、会话锁、请求回执与整轮提交 |
| 监控与评测 | 工具超时/缓存/熔断、路由降权、异步评测、Judge 与回归比较 |

工具提供知识检索、排障建议、账单字段检查及交接摘要。真实账户操作、扣款退款和工单系统需另行集成。开发模式中的 SaaS 政策是演示资料，可在知识管理页面导入自己的产品文档。

## 开发与验证

后端使用 Python 3.12，前端使用 Node.js 22.12+。完整 RAG 使用 Docker；Windows 的 `chromadb-client` 环境用于离线回归测试。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r SaaSBackend/requirements-dev-windows.txt
Push-Location SaaSBackend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
Pop-Location
cd SaaSFrontend
npm ci
npm test
npm run build
```

本次本地验证：后端 148 项、前端 14 项通过，Vite 生产构建通过。离线测试不代表真实模型质量或生产容量结论。

更多说明见 [文档导航](docs/README.md)、[开发指南](docs/development.md)、[部署与排障](docs/operations.md) 和 [代码阅读顺序](docs/code-reading-guide.md)。
