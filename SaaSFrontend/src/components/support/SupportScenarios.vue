<template>
  <aside class="support-directory" aria-label="支持场景">
    <div class="directory-title"><span class="kicker">SERVICE DIRECTORY</span><h2>找到你的问题方向</h2><p>选择场景，补充问题描述。</p></div>
    <div class="scenario-list">
      <button v-for="(scenario, index) in scenarios" :key="scenario.title" @click="$emit('select', scenario.prompt)">
        <span class="scenario-icon"><AppIcon :name="scenario.icon" /></span>
        <span class="scenario-copy"><strong>{{ scenario.title }}</strong><small>{{ scenario.description }}</small></span>
        <span class="scenario-number">0{{ index + 1 }}</span>
      </button>
    </div>
    <p class="directory-hint">场景入口会填入示例问题，具体处理角色由问题内容决定。</p>
    <div class="directory-resource">
      <span class="resource-symbol"><AppIcon name="book" /></span>
      <h3>有资料，回答才有依据</h3>
      <p>产品说明、接入文档和支持规范，为问题处理提供参考。</p>
      <div class="resource-counts"><span><strong>{{ knowledgeCount }}</strong>知识片段</span><span><strong>{{ skillCount || '—' }}</strong>支持规范</span></div>
      <button class="resource-link" @click="$emit('knowledge')">查看产品知识<AppIcon name="northeast" /></button>
    </div>
    <div class="directory-footer"><span></span>通用 · 技术 · 账单 · 人工交接</div>
  </aside>
</template>

<script setup>
import AppIcon from '../AppIcon.vue'
defineProps({ knowledgeCount: [String, Number], skillCount: Number })
defineEmits(['select', 'knowledge'])
const scenarios = [
  { title: '功能与使用', description: '功能说明 · 新用户引导', icon: 'book', prompt: '我是新用户，想了解产品功能和开始使用的步骤。' },
  { title: 'API 与技术', description: '接入指导 · 认证排障', icon: 'sliders', prompt: 'API 调用返回 401，应该提供哪些信息、如何排查？' },
  { title: '订阅与账单', description: '续费说明 · 费用与发票', icon: 'document', prompt: '我想了解订阅续费和账单核验需要哪些信息。' },
  { title: '企业账户', description: '账户使用 · 工作空间咨询', icon: 'route', prompt: '企业账户和工作空间如何使用？涉及成员权限调整时应如何处理？' }
]
</script>
