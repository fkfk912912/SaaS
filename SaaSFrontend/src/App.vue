<template>
  <div class="app-shell" :class="`view-${activeView}`">
    <WorkspaceHeader :views="views" :active-view="activeView" :health-ok="healthOk" :health-label="healthLabel" :user-id="settings.userId" :docs-url="docsUrl"
      @navigate="activeView = $event" @settings="openConnection" />
    <main class="workspace">
      <div v-if="toast" class="toast" role="status">
        <AppIcon name="chat" />
        {{ toast }}
      </div>
      <SupportWorkspace v-if="activeView === 'chat'" ref="supportWorkspace" v-model:draft="draft"
        :messages="messages" :busy="busy" :pending-action="pendingAction" :last-response="lastResponse" :last-trace="lastTrace"
        :monitor-data="monitorData" :knowledge-count="knowledgeCount" :skill-count="skillsData.count"
        @send="performAction('chat', sendMessage)" @clear="clearConversation" @inspect="inspectorDialog.showModal()"
        @refresh="loadMonitor" @copy="copyMessage" @use-prompt="usePrompt" @knowledge="activeView = 'knowledge'" />
      <KnowledgeCenter v-else-if="activeView === 'knowledge'" v-model:search-query="searchQuery" v-model:doc-title="docTitle" v-model:doc-content="docContent"
        :busy="busy" :pending-action="pendingAction" :knowledge-count="knowledgeCount" :search-results="searchResults" :searched="searched" :skills-data="skillsData"
        @search="performAction('search', searchKnowledge)" @import="performAction('import', submitKnowledge)" @upload="performAction('upload', handleUpload, $event)" @reload-skills="performAction('skills', reloadSkillSet)" />
      <QualityDashboard v-else :busy="busy" :pending-action="pendingAction" :eval-data="evalData" @run="performAction('evaluation', runEvaluation)" />
    </main>
    <dialog ref="inspectorDialog" class="inspector-dialog" @click="closeOnBackdrop" aria-labelledby="inspector-title">
      <div class="drawer-heading">
        <div>
          <AppIcon name="panel" />
          <h2 id="inspector-title">处理详情</h2>
        </div>
        <button class="icon-button" aria-label="关闭处理详情" @click="inspectorDialog.close()">
          <AppIcon name="close" />
        </button>
      </div>
      <RequestInspector :last-response="lastResponse" :last-trace="lastTrace" :busy="busy && pendingAction === 'chat'" :monitor-data="monitorData" @refresh="loadMonitor" />
    </dialog>
    <dialog ref="connectionDialog" class="connection-dialog" @click="closeOnBackdrop" aria-labelledby="connection-title">
      <div class="dialog-heading">
        <div>
          <span class="kicker">CONNECTION</span>
          <h2 id="connection-title">连接配置</h2>
        </div>
        <button class="icon-button" aria-label="关闭连接配置" @click="connectionDialog.close()">
          <AppIcon name="close" />
        </button>
      </div>
      <p class="dialog-description">配置 {{ currentBackend.label }} 服务与当前会话。</p>
      <form @submit.prevent="saveConnection">
        <label>
          <span>服务地址</span>
          <input v-model="connectionDraft.endpoint" required placeholder="/api/python 或 http://localhost:8000" />
          <small>使用代理路径或完整的 HTTP / HTTPS 地址。</small>
        </label>
        <label>
          <span>用户 ID</span>
          <input v-model="connectionDraft.userId" placeholder="u1001" />
        </label>
        <label>
          <span>会话 ID</span>
          <input v-model="connectionDraft.conversationId" placeholder="留空以自动生成" />
        </label>
        <label v-if="settings.backend === 'python'">
          <span>API 访问 Token（启用鉴权时填写，仅本页保存）</span>
          <input v-model="connectionDraft.pythonToken" type="password" autocomplete="off" placeholder="不是模型 API Key" />
        </label>
        <div class="dialog-health">
          <i :class="healthOk ? 'online' : 'offline'"></i>
          <span>{{ healthOk ? '服务已连接' : healthLabel }}</span>
          <button type="button" class="text-button" @click="checkHealth">
            检查当前连接
            <AppIcon name="refresh" />
          </button>
        </div>
        <details v-if="statusText" class="connection-detail">
          <summary>查看连接详情</summary>
          <pre>{{ statusText }}</pre>
        </details>
        <div class="dialog-actions">
          <button type="button" class="quiet-button" @click="connectionDialog.close()">取消</button>
          <button type="submit">
            保存配置
            <AppIcon name="check" />
          </button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  addKnowledge,
  backendMeta,
  createInitialSettings,
  reloadSkills,
  requestChat,
  requestHealth,
  requestKnowledgeStats,
  requestMonitor,
  requestSearch,
  requestToolTrace,
  requestSkills,
  runEvaluation as requestEvaluation,
  saveSettings,
  uploadKnowledge
} from './lib/backends'

import AppIcon from './components/AppIcon.vue'
import RequestInspector from './components/RequestInspector.vue'
import WorkspaceHeader from './components/layout/WorkspaceHeader.vue'
import SupportWorkspace from './views/SupportWorkspace.vue'
import KnowledgeCenter from './views/KnowledgeCenter.vue'
import QualityDashboard from './views/QualityDashboard.vue'

import { createRequestState } from './lib/requestState'

// 阅读导航：本入口协调页面、会话和网络请求；views 中的组件接收数据并上报用户操作。
// 配置可从浏览器恢复；消息数组仅属于当前页面生命周期，没有历史会话列表恢复功能。
const settings = reactive(createInitialSettings())
// 为每类请求保留快照与代次，切换连接或新会话后，旧响应不能覆盖新界面。
const requestState = createRequestState(settings)
const activeView = ref('chat')
const messages = ref([])
const draft = ref('')
const busy = ref(false)
const healthOk = ref(false)
const healthLabel = ref('未检查')
const statusText = ref('')
const knowledgeCount = ref('-')
const searchQuery = ref('API 登录报 401 如何排查')
const searchResults = ref([])
const docTitle = ref('')
const docContent = ref('')
const supportWorkspace = ref(null)
const connectionDialog = ref(null)
const inspectorDialog = ref(null)
const connectionDraft = reactive({ endpoint: '', userId: '', conversationId: '', pythonToken: '' })
const pendingAction = ref('')
const searched = ref(false)
const views = [
  { id: 'chat', label: '支持工作台', icon: 'chat' },
  { id: 'knowledge', label: '产品知识', icon: 'book' },
  { id: 'evaluation', label: '质量评测', icon: 'chart' }
]
const monitorData = ref({ agent_stats: {}, tool_stats: {}, active_alerts: [], suggestions: [] })
const skillsData = ref({ count: 0, skills: [], errors: [] })
const lastResponse = ref(null)
const lastTrace = ref(null)
const evalData = ref(null)
const toast = ref('')
let toastTimer
let messageSequence = 0

const currentBackend = computed(() => backendMeta(settings.backend, settings))
const docsUrl = computed(() => `${currentBackend.value.baseUrl}/docs`)

watch(() => settings.conversationId, persist)
onMounted(refreshConsole)
onBeforeUnmount(() => {
  requestState.invalidate()
  clearTimeout(toastTimer)
})

function persist() { saveSettings(settings) }

// 统一记录正在执行的界面动作，避免用户在同一操作尚未完成时重复提交。
// 这里的 busy 是前端交互状态；服务端仍需独立处理锁、幂等回执和超时。
function performAction(name, action, ...args) {
  if (busy.value) return
  pendingAction.value = name
  return action(...args)
}

function openConnection() {
  connectionDraft.pythonToken = settings.pythonToken
  connectionDraft.endpoint = currentBackend.value.baseUrl
  connectionDraft.userId = settings.userId
  connectionDraft.conversationId = settings.conversationId
  connectionDialog.value.showModal()
}

function closeOnBackdrop(event) {
  const dialog = event.currentTarget
  if (event.target !== dialog) return
  const rect = dialog.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close()
}

// 连接或用户身份变化时先使旧请求失效，再更新配置，防止把其他会话的结果显示过来。
// API 访问 Token 只用于应用接口鉴权，与后端配置的 DeepSeek 模型 Key 不同。
function saveConnection() {
  const endpoint = connectionDraft.endpoint.trim().replace(/\/+$/, '')
  if (!endpoint || !(endpoint.startsWith('/') || /^https?:\/\//i.test(endpoint))) {
    showToast('请输入代理路径或 HTTP / HTTPS 服务地址')
    return
  }
  const changed = connectionDraft.pythonToken !== settings.pythonToken || endpoint !== currentBackend.value.baseUrl || connectionDraft.userId.trim() !== settings.userId || connectionDraft.conversationId.trim() !== settings.conversationId
  if (changed) {
    requestState.invalidate()
    busy.value = false
    messages.value = []
    lastResponse.value = null
    lastTrace.value = null
    searchResults.value = []
    searched.value = false
    evalData.value = null
    monitorData.value = { agent_stats: {}, tool_stats: {}, active_alerts: [], suggestions: [] }
    skillsData.value = { count: 0, skills: [], errors: [] }
    knowledgeCount.value = '—'
    healthOk.value = false
    healthLabel.value = '未检查'
    statusText.value = ''
  }
  const identityChanged = connectionDraft.userId.trim() !== settings.userId || endpoint !== currentBackend.value.baseUrl
  settings.endpoints[settings.backend] = endpoint
  settings.pythonToken = connectionDraft.pythonToken.trim()
  settings.userId = connectionDraft.userId.trim()
  settings.conversationId = identityChanged && connectionDraft.conversationId.trim() === settings.conversationId ? '' : connectionDraft.conversationId.trim()
  persist()
  connectionDialog.value.close()
  refreshConsole()
  showToast('连接配置已保存')
}

async function copyMessage(content) {
  try {
    await navigator.clipboard.writeText(content)
    showToast('回复已复制')
  } catch {
    showToast('复制失败，请手动选择回复文字')
  }
}

// 健康、知识数量、监控与规范可独立读取；其中一个失败不应阻止其他面板刷新。
async function refreshConsole() {
  await Promise.allSettled([checkHealth(), loadStats(), loadMonitor(), loadSkills()])
}

async function checkHealth() {
  const request = requestState.begin('health')

  try {
    const data = await requestHealth(request.backend, request.settings)
    if (!request.isCurrent()) return
    healthOk.value = data.status === 'ok'
    healthLabel.value = data.status || 'ok'
    statusText.value = JSON.stringify(data, null, 2)
  } catch (error) {
    if (!request.isCurrent()) return
    // 健康检查只更新状态，保留用户选择的后端。
    healthOk.value = false
    healthLabel.value = '不可用'
    statusText.value = error.message
  }
}

async function loadStats() {
  const request = requestState.begin('stats')
  try {
    const data = await requestKnowledgeStats(request.backend, request.settings)
    if (!request.isCurrent()) return
    knowledgeCount.value = data.total_chunks ?? data.totalChunks ?? '-'
  } catch {
    if (request.isCurrent()) knowledgeCount.value = '-'
  }
}

async function loadMonitor() {
  const request = requestState.begin('monitor')
  try {
    const data = await requestMonitor(request.backend, request.settings)
    if (request.isCurrent()) monitorData.value = { ...data, loaded: true }
  } catch {
    if (request.isCurrent()) monitorData.value = { agent_stats: {}, tool_stats: {}, active_alerts: [], suggestions: [] }
  }
}

async function loadSkills() {
  const request = requestState.begin('skills')
  try {
    const data = await requestSkills(request.backend, request.settings)
    if (request.isCurrent()) skillsData.value = data
  } catch {
    if (request.isCurrent()) skillsData.value = { count: 0, skills: [], errors: [] }
  }
}

async function reloadSkillSet() {
  const request = requestState.begin('action')
  busy.value = true
  try {
    const data = await reloadSkills(request.backend, request.settings)
    if (!request.isCurrent()) return
    skillsData.value = data
    showToast('Skills 已重新加载')
  } catch (error) {
    if (!request.isCurrent()) return
    statusText.value = error.message
    showToast('Skills 加载失败')
  } finally { if (request.isCurrent()) busy.value = false }
}

// 流程：添加用户气泡 → requestChat → 按 request_id 查询工具轨迹 → 更新回复和监控。
// 页面先显示输入，不代表服务端已经提交这一轮；异常会通过错误气泡明确显示。
async function sendMessage() {
  const content = draft.value.trim()
  if (!content || busy.value) return
  messages.value.push({ id: createMessageId(), role: 'user', content })
  draft.value = ''
  lastResponse.value = null
  lastTrace.value = null
  nextTick(() => supportWorkspace.value?.scrollToLatest())
  const request = requestState.begin('action')
  busy.value = true
  try {
    const response = await requestChat(request.backend, request.settings, content)
    if (!request.isCurrent()) return
    if (response.conversationId && !settings.conversationId) {
      settings.conversationId = response.conversationId
      persist()
    }
    const trace = await loadToolTrace(response.requestId, request)
    if (!request.isCurrent()) return
    lastResponse.value = response
    lastTrace.value = trace
    const meta = [response.intent, response.primaryAgent || response.agentType, response.knowledgeUsed ? 'RAG' : '', response.escalated ? '转人工' : ''].filter(Boolean).join(' · ')
    messages.value.push({ id: createMessageId(), role: 'assistant', content: response.response, meta, trace: lastTrace.value?.trace || null })
    await loadMonitor()
  } catch (error) {
    if (!request.isCurrent()) return
    messages.value.push({ id: createMessageId(), role: 'assistant', content: error.message, meta: '请求失败', error: true })
  } finally {
    if (!request.isCurrent()) return
    busy.value = false
    await nextTick()
    supportWorkspace.value?.scrollToLatest()
  }
}

// 场景入口只填草稿并聚焦，不发送请求，也不固定后端选择哪一个 Agent。
function usePrompt(prompt) { draft.value = prompt; nextTick(() => supportWorkspace.value?.focusComposer()) }

// 清除当前显示并重置会话 ID；不会在此删除 Redis 或 ChromaDB 中的已有数据。
function clearConversation() {
  requestState.invalidate()
  busy.value = false
  messages.value = []
  lastResponse.value = null
  lastTrace.value = null
  settings.conversationId = ''
  persist()
}

async function searchKnowledge() {
  if (!searchQuery.value.trim() || busy.value) return
  const request = requestState.begin('action')
  busy.value = true
  try {
    const data = await requestSearch(request.backend, request.settings, searchQuery.value, 5)
    if (!request.isCurrent()) return
    searchResults.value = data.results || []
    searched.value = true
    showToast(`检索完成，返回 ${searchResults.value.length} 条结果`)
  } catch (error) {
    if (!request.isCurrent()) return
    statusText.value = error.message
    showToast('检索失败，请检查连接')
  } finally { if (request.isCurrent()) busy.value = false }
}

async function submitKnowledge() {
  if (!docTitle.value.trim() || !docContent.value.trim() || busy.value) return
  const request = requestState.begin('action')
  busy.value = true
  try {
    const data = await addKnowledge(request.backend, request.settings, [{ title: docTitle.value.trim(), content: docContent.value.trim() }])
    if (!request.isCurrent()) return
    statusText.value = JSON.stringify(data, null, 2)
    await loadStats()
    if (!request.isCurrent()) return
    showToast('文档已添加')
  } catch (error) {
    if (!request.isCurrent()) return
    statusText.value = error.message
    showToast('文档导入失败')
  } finally { if (request.isCurrent()) busy.value = false }
}

async function handleUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || busy.value) return
  if (file.size > 10 * 1024 * 1024) { showToast('文件不能超过 10 MB'); return }
  const request = requestState.begin('action')
  busy.value = true
  try {
    const data = await uploadKnowledge(request.backend, request.settings, file)
    if (!request.isCurrent()) return
    statusText.value = JSON.stringify(data, null, 2)
    await loadStats()
    if (!request.isCurrent()) return
    showToast(`${file.name} 导入成功`)
  } catch (error) {
    if (!request.isCurrent()) return
    statusText.value = error.message
    showToast('文件导入失败')
  } finally { if (request.isCurrent()) busy.value = false }
}

// 提交或接续异步评测任务，展示后端报告；评分规则和通过阈值不在页面里计算。
async function runEvaluation() {
  const request = requestState.begin('action')
  busy.value = true
  try {
    const data = await requestEvaluation(request.backend, request.settings, null, {
      isCurrent: request.isCurrent,
      onProgress: job => {
        if (request.isCurrent()) statusText.value = `评测任务 ${job.job_id}：${job.status === 'queued' ? '排队中' : '运行中'}，已完成 ${job.completed}/${job.total} 组`
      }
    })
    if (!request.isCurrent()) return
    evalData.value = data
    showToast(data.status === 'failed' ? '评测执行失败，请查看结果' : data.status === 'partial' ? '评测部分完成，请查看失败原因' : '评测完成')
  } catch (error) {
    if (!request.isCurrent()) return
    statusText.value = error.message
    showToast('评测运行失败')
  } finally { if (request.isCurrent()) busy.value = false }
}

async function loadToolTrace(requestId, request = requestState.begin('trace')) {
  try {
    return await requestToolTrace(request.backend, request.settings, requestId)
  } catch {
    return null
  }
}

function createMessageId() {
  messageSequence += 1
  return `message-${Date.now()}-${messageSequence}`
}

function showToast(message) {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2600)
}
</script>
