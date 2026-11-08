<template>
      <section class="page page-knowledge">
        <div class="page-heading">
          <div class="heading-copy">
            <span class="kicker">KNOWLEDGE OPERATIONS</span>
            <h1>产品知识中心</h1>
            <p>管理业务知识，为每次回答提供依据。</p>
          </div>
          <div class="count-display">
            <strong>{{ knowledgeCount }}</strong>
            <span>知识片段</span>
          </div>
        </div>
        <div class="knowledge-layout">
          <section class="workspace-card search-workspace">
            <div class="card-heading">
              <div>
                <span class="kicker">RETRIEVAL</span>
                <h2>检索知识</h2>
              </div>
              <AppIcon name="search" />
            </div>
            <form class="search-line" @submit.prevent="$emit('search')">
              <input v-model="searchQuery" aria-label="检索问题" placeholder="例如：订阅续费如何处理" />
              <button :disabled="busy || !searchQuery.trim()">
                <AppIcon name="search" />
                {{ busy && pendingAction === 'search' ? '检索中' : '搜索' }}
              </button>
            </form>
            <div v-if="searchResults.length" class="result-list">
              <article v-for="(item, index) in searchResults" :key="item.id || index" class="result-item">
                <span class="result-number">{{ String(index + 1).padStart(2, '0') }}</span>
                <div>
                  <div class="result-title">
                    <strong>{{ item.title || '未命名文档' }}</strong>
                    <small>相关度 {{ item.score ?? '—' }}</small>
                  </div>
                  <p>{{ item.content }}</p>
                </div>
              </article>
            </div>
            <div v-else class="workspace-empty">
              <AppIcon name="book" />
              <h3>{{ searched ? '暂未找到相关知识' : '搜索你的知识库' }}</h3>
              <p>{{ searched ? '尝试换一个问题，或添加更多知识文档。' : '输入客户问题，查看最相关的知识片段。' }}</p>
            </div>
          </section>
          <section class="workspace-card import-workspace">
            <div class="card-heading">
              <div>
                <span class="kicker">INGESTION</span>
                <h2>添加知识</h2>
              </div>
              <AppIcon name="document" />
            </div>
            <form @submit.prevent="$emit('import')">
              <label>
                <span>文档标题</span>
                <input v-model="docTitle" required placeholder="例如：API 接入说明" />
              </label>
              <label>
                <span>知识内容</span>
                <textarea v-model="docContent" required rows="7" placeholder="输入客服规范、产品说明或排障流程"></textarea>
              </label>
              <div class="side-actions">
                <button :disabled="busy || !docTitle.trim() || !docContent.trim()">
                  <AppIcon name="arrow" />
                  {{ busy && pendingAction === 'import' ? '添加中' : '添加文档' }}
                </button>
                <label class="upload-button" :class="{ disabled: busy }">
                  <AppIcon name="upload" />
                  上传文件
                  <input :disabled="busy" type="file" accept=".txt,.md,.json" @change="$emit('upload', $event)" />
                </label>
              </div>
              <p class="form-hint">支持 TXT、Markdown、JSON，最大 10 MB。</p>
            </form>
          </section>
        </div>
        <section class="workspace-card skills-workspace">
          <div class="card-heading">
            <div>
              <span class="kicker">LOADED SKILLS</span>
              <h2>支持规范</h2>
            </div>
            <button class="text-button" :disabled="busy" @click="$emit('reload-skills')">
              <AppIcon name="refresh" />
              重新加载
            </button>
          </div>
          <div class="skill-table">
            <div v-for="skill in skillsData.skills" :key="skill.name" class="skill-item">
              <span class="skill-dot"></span>
              <strong>{{ skill.name }}</strong>
              <span>{{ skill.description || '业务规范能力' }}</span>
              <small>{{ skill.content_chars || 0 }} chars</small>
            </div>
            <p v-if="!skillsData.skills?.length" class="skills-empty">暂无已加载规范，连接服务后刷新查看。</p>
          </div>
        </section>
      </section>
</template>

<script setup>
import AppIcon from '../components/AppIcon.vue'
// 知识页面展示查询结果和规范信息，实际检索、导入、上传仍由父级调用既有接口。
defineProps({
  busy: Boolean, pendingAction: String, knowledgeCount: [String, Number],
  searchResults: { type: Array, default: () => [] }, searched: Boolean,
  skillsData: { type: Object, required: true }
})
defineEmits(['search', 'import', 'upload', 'reload-skills'])
const searchQuery = defineModel('searchQuery', { type: String, default: '' })
const docTitle = defineModel('docTitle', { type: String, default: '' })
const docContent = defineModel('docContent', { type: String, default: '' })
</script>
