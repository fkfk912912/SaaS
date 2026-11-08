<template>
  <header class="workspace-header">
    <a class="workspace-brand" href="#" @click.prevent="$emit('navigate', 'chat')" aria-label="栈桥首页">
      <svg class="bridge-logo" viewBox="0 0 40 40" fill="none" aria-hidden="true">
        <path d="M7 28V12M33 28V12M7 21C13 21 13 13 20 13S27 21 33 21M7 28H33M14 20V28M20 14V28M26 20V28" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" />
      </svg>
      <span><strong>栈桥</strong><small>STACKBRIDGE</small></span>
    </a>
    <nav class="workspace-nav" aria-label="主导航">
      <button v-for="view in views" :key="view.id" :class="{ active: activeView === view.id }"
        :aria-current="activeView === view.id ? 'page' : undefined" @click="$emit('navigate', view.id)">
        <AppIcon :name="view.icon" /><span>{{ view.label }}</span>
      </button>
    </nav>
    <div class="workspace-account">
      <span class="service-status"><i :class="{ online: healthOk }"></i>{{ healthOk ? '服务已连接' : healthLabel === '未检查' ? '正在连接' : '服务未连接' }}</span>
      <a :href="docsUrl" target="_blank" rel="noreferrer" class="header-docs" aria-label="API 文档"><AppIcon name="document" /></a>
      <button class="header-settings" @click="$emit('settings')" aria-label="连接配置" title="连接配置"><AppIcon name="sliders" /></button>
      <span class="account-divider"></span>
      <button class="account-avatar" @click="$emit('settings')" :aria-label="`当前用户 ${userId || 'anonymous'}，打开连接配置`">{{ (userId || 'U').slice(0, 1).toUpperCase() }}</button>
    </div>
  </header>
</template>

<script setup>
import AppIcon from '../AppIcon.vue'
defineProps({ views: Array, activeView: String, healthOk: Boolean, healthLabel: String, userId: String, docsUrl: String })
defineEmits(['navigate', 'settings'])
</script>
