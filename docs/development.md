# 开发指南

## 依赖与测试

要求 Python 3.12；前端要求 Node.js 22.12+。完整服务用根目录 Compose 启动，避免在 Windows 安装完整 Chroma 本地存储依赖。

Windows 在项目根目录执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r SaaSBackend/requirements-dev-windows.txt
Push-Location SaaSBackend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
Pop-Location
```

Linux 在项目根目录执行：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r SaaSBackend/requirements-dev.txt
cd SaaSBackend
../.venv/bin/python -m pytest -q -p no:cacheprovider
```

前端在 `SaaSFrontend/` 执行 `npm ci`、`npm test` 和 `npm run build`。开发服务 `npm run dev` 将 API 请求代理到 8010；后端服务需另外启动。

后端回归使用录制式模型、fakeredis 和本地 MCP 夹具；协议测试使用真实 SDK 与离线 HTTP 传输。正常回归不需要模型密钥，也不产生真实模型效果评分。

## 修改约定

- 路由和业务逻辑分别放在 `api/` 与对应领域模块，工具定义与工具执行保持职责清楚。
- API 字段有变更时，同时检查 `SaaSFrontend/src/lib/backends.js` 和请求状态处理。
- 添加 Skills 时遵循 [Skills 说明](../SaaSBackend/skills/README.md)，修改后检查加载和角色权限。
- 前端依赖使用 npm 和提交的 `package-lock.json`；提交前运行现有测试和构建。
- `.env`、会话数据、模型轨迹、历史快照和构建目录属于本机文件。

建议持续集成执行上述后端回归、前端 Node 测试和 Vite 构建。真实模型评测应另行记录模型 ID、数据来源、提示词版本、样本划分及失败样本，避免把离线回归结果当作效果结论。

## 本次验证范围

2026-11-08：Windows 后端回归 148 项通过；Node 前端回归 14 项通过；Vite 生产构建通过。此次整理没有重新执行付费模型评测。
