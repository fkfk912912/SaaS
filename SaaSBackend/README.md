# SaaS Python 后端

Python 3.12 / FastAPI / LangChain。完整部署与模型配置见 [项目 README](../README.md)，模块说明见 [架构](../docs/architecture.md)，测试命令见 [开发指南](../docs/development.md)。

从 `api/main.py` 的聊天入口阅读，再依次跟进 `core/intent_recognizer.py`、`agents/agent_orchestrator.py` 与 `agents/langchain_runtime.py`。

`requirements.txt` 用于 Linux / Docker 完整运行；`requirements-windows.txt` 仅提供 Windows Chroma HTTP 客户端。开发测试分别使用 `requirements-dev.txt` 和 `requirements-dev-windows.txt`。
