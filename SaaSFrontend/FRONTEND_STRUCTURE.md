# 栈桥支持工作台：前端结构说明

页面采用顶部导航、左侧支持场景、右侧会话工作区。聊天、知识管理、支持规范、监测详情和质量评测继续使用原有后端接口。

## 从哪里开始读

| 文件 | 职责 | 原来的位置 |
| --- | --- | --- |
| `src/App.vue` | 当前页面、会话和请求状态；协调各页面事件与后端请求 | 原 App.vue 的状态与方法 |
| `src/components/layout/WorkspaceHeader.vue` | 顶部导航、服务连接状态、文档与连接设置入口 | 原 App.vue 的侧边导航、顶栏 |
| `src/views/SupportWorkspace.vue` | 消息、输入框、发送、清空、处理详情入口 | 原 App.vue 的聊天页面 |
| `src/components/support/SupportScenarios.vue` | 四个场景的示例问题入口、真实知识数量与规范数量 | 原首页提示入口的业务化展示 |
| `src/components/support/SupportWelcome.vue` | 会话为空时的引导 | 原首页欢迎区 |
| `src/views/KnowledgeCenter.vue` | 检索、文档导入、上传、支持规范重载 | 原 App.vue 的知识页面 |
| `src/views/QualityDashboard.vue` | 评测按钮、结果、评分错误、回归信息 | 原 App.vue 的评测页面 |
| `src/components/RequestInspector.vue` | 现有请求追踪、工具调用和监控数据展示 | 继续复用 |
| `src/lib/backends.js` | 原有 HTTP 接口、请求回执 ID、字段适配、评测任务查询 | 保持原实现 |
| `src/lib/requestState.js` | 连接或会话切换时忽略旧请求的返回 | 保持原实现 |
| `src/styles/base.css` | 颜色变量和基础控件 | 从旧 styles.css 拆分 |
| `src/styles/panels.css` | 知识、评测、处理详情与对话框样式 | 从旧 styles.css 拆分并调整 |
| `src/styles/workspace.css` | 新导航、支持场景、会话及响应式布局 | 新的工作台设计 |

## 一条消息的调用顺序

1. 点击场景时只填入问题草稿，输入框获得焦点；此时不会发送请求，也不会固定 Agent 路由。
2. 用户点击发送或按 Ctrl/Command + Enter，SupportWorkspace 发出 send 事件。
3. App.vue 中的 sendMessage 沿用原来的请求管理和 client_request_id 逻辑。
4. backends.js 请求现有 `/chat`，返回后读取原有工具追踪与监控接口。
5. App.vue 更新消息和追踪数据，SupportWorkspace 与 RequestInspector 根据传入的数据展示。

视图通过 props 接收数据，通过事件通知入口；表单草稿通过 v-model 同步。页面间切换不会清空 App.vue 保存的会话。
