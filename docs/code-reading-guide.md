# 栈桥主要代码阅读顺序

主要模块中的中文注释提供阅读导航。文件顶部的“阅读导航”说明职责和入口；函数内注释解释设计原因、失败分支和容易混淆的统计口径。

## 先跟着一条请求走

| 顺序 | 文件 | 重点入口 | 主要理解什么 |
| --- | --- | --- | --- |
| 1 | [前端入口](../SaaSFrontend/src/App.vue) | sendMessage | 页面如何发起请求、展示回复与处理错误 |
| 2 | [HTTP 适配](../SaaSFrontend/src/lib/backends.js) | requestChat | 请求字段、客户端提交 ID、返回字段适配 |
| 3 | [聊天接口](../SaaSBackend/api/main.py) | chat | 身份、会话锁、回执、上下文、执行与提交 |
| 4 | [意图识别](../SaaSBackend/core/intent_recognizer.py) | recognize、_vote | 三路证据、业务组投票、细意图与降级 |
| 5 | [业务状态](../SaaSBackend/core/conversation_state.py) | merge_state | 上一轮字段什么时候继承、什么时候清理 |
| 6 | [Agent 编排](../SaaSBackend/agents/agent_orchestrator.py) | run、_route_decision、_execute | 四个角色、主辅协作、失败兜底与升级 |
| 7 | [LangChain 执行](../SaaSBackend/agents/langchain_runtime.py) | run_agent | 模型与工具循环、权限、预算与轨迹 |
| 8 | [工具定义](../SaaSBackend/agents/tools.py) | build_shared_rag_tools | 模型看见的工具与实际执行函数怎样连接 |
| 9 | [增强检索](../SaaSBackend/tooling/tool_manager.py) | search_with_rewrite | 改写、多路召回、去重、重排与失败处理 |
| 10 | [基础知识库](../SaaSBackend/tooling/knowledge_base.py) | search、add_documents | 文档身份、向量查询、片段更新与线程池 |
| 11 | [记忆提交](../SaaSBackend/memory/conversation_memory.py) | commit_turn、_compress | 一轮原子保存、摘要压缩及并发新消息保护 |

## 再看横向能力

- [统一模型接入](../SaaSBackend/core/llm_client.py)：OpenAI 兼容协议、DeepSeek 字段适配和辅助文本任务。
- [意图向量](../SaaSBackend/core/intent_embedding.py)：远程/本地降级时保持问题和模板处于同一向量空间。
- [并发与后台任务](../SaaSBackend/core/concurrency.py)：进程内锁、Redis 可续租锁、有界维护队列。
- [动态规则](../SaaSBackend/core/skill_loader.py)：按角色和关键词加载 Skills，并控制注入字符预算。
- [MCP 客户端](../SaaSBackend/tooling/mcp_client.py)：连接、发现、注册、调用和断线恢复。
- [MCP 服务端](../SaaSBackend/tooling/mcp_server.py)：向其他客户端提供本地知识查询及统计资源。
- [在线监控](../SaaSBackend/monitor/performance_monitor.py)：累计告警、近期窗口、路由降权的区别。
- [评测器](../SaaSBackend/evaluation/evaluator.py)：分类指标、Judge、通过条件、评分错误和回归比较。
- [评测任务](../SaaSBackend/evaluation/jobs.py)：提交任务 ID、串行执行和状态查询。
