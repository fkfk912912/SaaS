<template>
      <section class="page-chat">
        <SupportScenarios :knowledge-count="knowledgeCount" :skill-count="skillCount" @select="$emit('use-prompt', $event)" @knowledge="$emit('knowledge')" />
        <div class="support-main">
        <div class="chat-toolbar">
          <span class="conversation-label"><span class="session-dot"></span>
            {{ messages.length ? '支持会话' : '支持工作台' }}
            <span v-if="messages.length" class="conversation-count">{{ messages.length }} 条消息</span>
          </span>
          <div class="chat-toolbar-actions">
            <button class="icon-button" @click="$emit('clear')" aria-label="新对话" title="新对话">
              <AppIcon name="compose" />
            </button>
            <button class="trace-toggle" @click="$emit('inspect')">
              <AppIcon name="panel" />
              <span>处理详情</span>
            </button>
          </div>
        </div>
        <div class="conversation-layout" :class="{ 'has-conversation': messages.length }">
          <section class="conversation" :class="{ 'is-empty': !messages.length }" aria-label="客服对话">
            <div class="messages" ref="messageList" role="log" aria-label="对话消息" aria-live="polite" :aria-busy="busy && pendingAction === 'chat'">
              <SupportWelcome v-if="!messages.length" />
              <template v-else>
                <article v-for="item in messages" :key="item.id" :class="['message', item.role, { 'message-error': item.error }]">
                  <span v-if="item.role === 'assistant'" class="message-avatar" aria-hidden="true">栈</span>
                  <div class="message-content">
                    <div class="message-meta">
                      <strong>{{ item.role === 'user' ? '你' : '栈桥助手' }}</strong>
                      <span v-if="item.error" class="error-label">请求失败</span>
                      <small v-else-if="item.role === 'assistant'">支持助手</small>
                    </div>
                    <p>{{ item.content }}</p>
                    <span v-if="item.meta && !item.error" class="agent-tag">
                      <AppIcon name="route" />
                      {{ item.meta }}
                    </span>
                    <details v-if="item.trace?.toolCalls?.length || item.trace?.toolsUsed?.length" class="message-trace">
                      <summary>
                        <AppIcon name="chevron" />
                        <span>工具调用</span>
                        <span class="count-tag">{{ item.trace.toolCalls?.length || 0 }}</span>
                      </summary>
                      <div v-for="(call, index) in item.trace.toolCalls" :key="`${item.id}-${index}`" class="trace-call-item">
                        <div class="trace-call-meta">
                          <strong>{{ call.tool_name || 'unknown_tool' }}</strong>
                          <span :class="call.success ? 'success' : 'danger'">{{ call.success ? '成功' : '失败' }}</span>
                        </div>
                        <pre>{{ formatJson(call.input || {}) }}</pre>
                      </div>
                      <p v-if="!item.trace.toolCalls?.length" class="muted">已调用：{{ item.trace.toolsUsed.join(' · ') }}</p>
                    </details>
                    <button
                      v-if="item.role === 'assistant' && !item.error"
                      class="icon-button copy-button"
                      @click="$emit('copy', item.content)"
                      aria-label="复制回复"
                      title="复制回复"
                    >
                      <AppIcon name="copy" />
                    </button>
                  </div>
                </article>
                <div v-if="busy && pendingAction === 'chat'" class="thinking" role="status">
                  <span class="message-avatar" aria-hidden="true">栈</span>
                  <span class="thinking-dots">
                    <i></i>
                    <i></i>
                    <i></i>
                  </span>
                  <span>正在处理问题</span>
                </div>
              </template>
            </div>
            <div class="composer-area">
              <form class="composer" @submit.prevent="$emit('send')">
                <textarea
                  ref="composerInput"
                  v-model="draft"
                  rows="2"
                  aria-label="客户问题"
                  placeholder="描述你遇到的问题，例如：API 返回 401，应该如何排查？"
                  @keydown.meta.enter.prevent="$emit('send')"
                  @keydown.ctrl.enter.prevent="$emit('send')"
                >
                </textarea>
                <div class="composer-bottom">
                  <span class="routing-label">
                    <AppIcon name="route" />
                    自动匹配支持角色
                  </span>
                  <div class="send-controls">
                    <span class="keyboard-hint">⌘ / Ctrl + Enter</span>
                    <button
                      class="send-button"
                      type="submit"
                      :disabled="busy || !draft.trim()"
                      :aria-label="busy && pendingAction === 'chat' ? '处理中' : '发送'"
                      :title="busy && pendingAction === 'chat' ? '处理中' : '发送'"
                    >
                      <AppIcon :name="busy && pendingAction === 'chat' ? 'refresh' : 'arrow'" :class="{ spinning: busy && pendingAction === 'chat' }" />
                    </button>
                  </div>
                </div>
              </form>
              <p class="composer-note">请勿发送密码、验证码或完整密钥。回复请结合产品资料核实。</p>
            </div>
          </section>
          <aside v-if="messages.length" class="inspector-desktop" aria-label="请求追踪与运行状态">
            <div class="inspector-heading">
              <AppIcon name="panel" />
              <h2>处理详情</h2>
            </div>
            <RequestInspector :last-response="lastResponse" :last-trace="lastTrace" :busy="busy && pendingAction === 'chat'" :monitor-data="monitorData" @refresh="$emit('refresh')" />
          </aside>
        </div>
        </div>
      </section>
</template>

<script setup>
import { ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import RequestInspector from '../components/RequestInspector.vue'
import SupportScenarios from '../components/support/SupportScenarios.vue'
import SupportWelcome from '../components/support/SupportWelcome.vue'
// 展示组件：消息和执行结果由 App.vue 传入；发送、清空、复制等动作通过事件交回入口。
defineProps({
  messages: { type: Array, default: () => [] }, busy: Boolean, pendingAction: String,
  lastResponse: { type: Object, default: null }, lastTrace: { type: Object, default: null },
  monitorData: { type: Object, required: true }, knowledgeCount: [String, Number], skillCount: Number
})
defineEmits(['send', 'clear', 'inspect', 'refresh', 'copy', 'use-prompt', 'knowledge'])
// 草稿双向绑定到父级，页面切换后仍由父级维护；组件本身不额外保存一份会话。
const draft = defineModel('draft', { type: String, default: '' })
const messageList = ref(null)
const composerInput = ref(null)
function scrollToLatest() { messageList.value?.scrollTo({ top: messageList.value.scrollHeight, behavior: 'smooth' }) }
function focusComposer() { composerInput.value?.focus() }
function formatJson(value) { return JSON.stringify(value ?? {}, null, 2) }
// 只暴露滚动与焦点操作，父级无需直接依赖子组件内部的 DOM 布局。
defineExpose({ scrollToLatest, focusComposer })
</script>
