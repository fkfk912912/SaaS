# 部署与排障

## 配置

复制 `SaaSBackend/.env.example` 为同目录 `.env`，填写自己的模型密钥、服务地址和可用模型 ID。Compose 插值使用 `--env-file SaaSBackend/.env`；后端同时从该文件接收环境变量。

`ECHOMIND_ENV=development` 允许演示数据与本地开发行为。向其他用户部署时使用 `production`，并通过 `ECHOMIND_API_TOKENS` 配置用户与管理员 Token；鉴权实现见 `SaaSBackend/core/access.py`。模型密钥与访问工作台的 API Token 用途不同。

`config/mcp_servers.json` 默认启用 Microsoft Learn 文档 MCP。离线运行可设置 `MCP_EXTERNAL_ENABLED=false`。修改 `.env` 后重新创建后端容器；仅重启不会更新 Compose 注入的环境变量。

## 常用命令

在项目根目录执行：

```sh
docker compose --env-file SaaSBackend/.env ps
docker compose --env-file SaaSBackend/.env logs --tail 100 echomind
docker compose --env-file SaaSBackend/.env up -d --build
docker compose --env-file SaaSBackend/.env up -d --force-recreate echomind
docker compose --env-file SaaSBackend/.env down
```

`/health` 检查服务状态，不能证明模型 Key 有效。需要在工作台发送一条消息，查看处理详情中的 Agent、工具调用和失败状态，才能确认实际模型链路。

| 现象 | 检查方向 |
| --- | --- |
| 模型 401 / 403 | 密钥、服务地址、模型权限，更新后重新创建容器 |
| 模型 429 / 超时 | 额度、限流、服务延迟与配置中的阶段预算 |
| Chroma 连接失败 | `docker compose ps` 与 chromadb 容器日志 |
| 页面出现 API 502 | 后端健康状态和 Nginx 内部 `echomind:8000` 连接 |
| 查不到企业资料 | 先在知识管理页面导入实际产品文档 |
| Windows RAG 不可用 | 完整存储运行在 Docker，Windows 依赖仅用于客户端和测试 |

## 本机数据与清理

依赖环境 `.venv/`、`SaaSFrontend/node_modules/` 和构建输出 `dist/` 可以按安装命令重建。运行中的数据库、Docker 磁盘和数据卷应按业务数据管理。

本机历史环境中 `validation/template-eval-20261107/docker-data/` 和 `docker-local/` 被 Docker Desktop 使用，因此保留原路径并整目录忽略。新克隆不包含这些文件，也不依赖这些目录启动；历史报告和源码快照已经移到项目外归档。
