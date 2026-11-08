<template>
      <section class="page page-evaluation">
        <div class="page-heading">
          <div class="heading-copy">
            <span class="kicker">EVALUATION LAB</span>
            <h1>质量评测</h1>
            <p>检查意图识别、回复质量与回归结果。</p>
          </div>
          <button @click="$emit('run')" :disabled="busy">
            <AppIcon :name="busy && pendingAction === 'evaluation' ? 'refresh' : 'play'" :class="{ spinning: busy && pendingAction === 'evaluation' }" />
            {{ busy && pendingAction === 'evaluation' ? '评测运行中' : '运行评测' }}
          </button>
        </div>
        <div v-if="evalData" class="evaluation-content">
          <div class="evaluation-summary">
            <div class="score-hero">
              <span>PASS RATE · 通过率</span>
              <strong :class="{ 'no-score': evalData.valid_total === 0 }">{{ evalData.valid_total === 0 ? '无有效评分' : formatPercent(evalData.pass_rate) }}</strong>
              <small>{{ evalData.passed }} / {{ evalData.valid_total ?? evalData.total }} 有效用例通过</small>
            </div>
            <div>
              <span>通过用例</span>
              <strong>{{ evalData.passed }}</strong>
            </div>
            <div>
              <span>总数 / 评分失败</span>
              <strong>
                {{ evalData.total }}
                <small> / {{ evalData.evaluation_errors ?? 0 }}</small>
              </strong>
            </div>
            <div>
              <span>回归问题</span>
              <strong :class="evalData.regressions?.length ? 'danger' : 'success'">{{ evalData.regressions?.length || 0 }}</strong>
            </div>
          </div>
          <div class="evaluation-layout">
            <section class="workspace-card">
              <div class="card-heading">
                <div>
                  <span class="kicker">QUALITY SCORES</span>
                  <h2>平均评分</h2>
                </div>
              </div>
              <p v-if="!Object.keys(evalData.avg_scores || {}).length" class="muted">没有有效评分，请查看失败原因。</p>
              <div class="score-list">
                <div v-for="(value, key) in evalData.avg_scores" :key="key">
                  <span>{{ key }}</span>
                  <i>
                    <b :style="{ width: `${Math.max(0, Math.min(Number(value) * 100, 100))}%` }"></b>
                  </i>
                  <strong>{{ Number(value).toFixed(2) }}</strong>
                </div>
              </div>
            </section>
            <section class="workspace-card">
              <div class="card-heading">
                <div>
                  <span class="kicker">RECOMMENDATIONS</span>
                  <h2>优化建议</h2>
                </div>
              </div>
              <p v-if="evalData.regression_note" class="muted">{{ evalData.regression_note }}</p>
              <div v-if="evalData.recommendations?.length" class="recommendations">
                <p v-for="(item, index) in evalData.recommendations" :key="index">{{ item }}</p>
              </div>
              <p v-else class="muted">本次评测没有返回额外建议。</p>
              <div v-for="(result, index) in evalData.regressions || []" :key="index" class="evaluation-warning">
                <strong class="danger">回归问题</strong>
                <p>{{ typeof result === 'string' ? result : formatJson(result) }}</p>
              </div>
              <div v-for="result in (evalData.results || []).filter(item => item.metadata?.judge_failed)" :key="result.test_id" class="evaluation-warning">
                <strong class="danger">{{ result.test_id }}：评分失败</strong>
                <p>{{ result.metadata.judge_error || '模型未返回有效评分' }}</p>
                <small>{{ result.metadata.judge_attempts ?? '—' }} 次尝试</small>
              </div>
            </section>
          </div>
        </div>
        <div v-else class="evaluation-empty">
          <span class="empty-emblem">
            <AppIcon name="chart" />
          </span>
          <h2>{{ busy && pendingAction === 'evaluation' ? '正在检验每一份答案。' : '了解 Agent 的表现' }}</h2>
          <p>{{ busy && pendingAction === 'evaluation' ? '评测需要一些时间，结果返回后会显示在这里。' : '运行一次评测，了解 Agent 的表现与改进空间。' }}</p>
          <div class="evaluation-dimensions">
            <span>意图识别</span>
            <span>回复质量</span>
            <span>回归检测</span>
          </div>
        </div>
      </section>
</template>

<script setup>
import AppIcon from '../components/AppIcon.vue'
// 报告来自后端：本组件只展示有效用例、评分错误、四维分数和回归信息。
// formatPercent 仅格式化显示，不会改变后端通过条件或修补失败评分。
defineProps({ busy: Boolean, pendingAction: String, evalData: { type: Object, default: null } })
defineEmits(['run'])
function formatPercent(value) {
  const number = Number(value || 0)
  return `${(number <= 1 ? number * 100 : number).toFixed(1)}%`
}
function formatJson(value) { return JSON.stringify(value ?? {}, null, 2) }
</script>
