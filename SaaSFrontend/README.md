# SaaS Vue 前端

要求 Node.js 22.12+。在本目录执行：

```sh
npm ci
npm run dev
```

开发页面为 http://localhost:5173；默认将 `/api/python` 代理至 http://localhost:8010。可通过 `VITE_PYTHON_API_URL` 指定其他后端地址。

`npm test` 运行 Node 离线测试，`npm run build` 构建 `dist/`。完整部署的页面端口为 5175，部署方式见 [项目说明](../README.md)。组件与请求分工见 [前端结构说明](FRONTEND_STRUCTURE.md)。
