<template>
  <section class="view">
    <div class="profile-banner">
      <div><span class="avatar large">{{ initial }}</span><div><h2>{{ username }}的学习画像</h2><p>{{ profileText }}</p><span>数据会随诊断、练习和订正持续更新</span></div></div>
      <button class="white-btn" @click="$emit('edit')">编辑基础信息</button>
    </div>
    <div v-if="loading" class="panel state-box">正在加载学习画像…</div>
    <template v-else>
      <div class="profile-cards">
        <article class="panel mastery-card"><div class="donut"><span><strong>{{ trend.current_score || 0 }}</strong><small>总体掌握度</small></span></div><div><h3>{{ statusText }}</h3><p>最近 {{ trendDays }} 天掌握度{{ trend.change >= 0 ? '提升' : '变化' }} {{ Math.abs(trend.change || 0) }} 分。</p><div class="legend"><span><i class="red-dot"></i>基础薄弱</span><span><i class="amber-dot"></i>正在巩固</span><span><i class="green-dot"></i>掌握良好</span></div></div></article>
        <article class="panel trend"><div class="panel-head"><div><h3>掌握度趋势</h3><p>最近 {{ trendDays }} 天变化</p></div><b :class="trend.change >= 0 ? 'up' : 'warn'">{{ trend.change >= 0 ? '↗ +' : '↘ ' }}{{ trend.change || 0 }}</b></div><div v-if="trend.points?.length" class="fake-chart"><span v-for="point in trend.points" :key="point.date" :style="{height: Math.max(6, point.score) + '%'}" :title="`${point.date}: ${point.score}`"></span></div><div v-else class="empty-small">完成练习后生成趋势</div></article>
      </div>
      <article class="panel knowledge-table">
        <div class="panel-head"><div><h3>知识点掌握情况</h3><p>共 {{ total }} 个已学习知识点</p></div><div class="filters"><button v-for="item in filters" :key="item.value" :class="{active: filter === item.value}" @click="setFilter(item.value)">{{ item.label }}</button></div></div>
        <div class="subject-tabs">
          <span>{{ profile?.stage === 'university' ? '课程' : '学科' }}</span>
          <button :class="{active:subjectFilter===''}" @click="subjectFilter=''">全部</button>
          <button v-for="item in subjectOptions" :key="item" :class="{active:subjectFilter===item}" @click="subjectFilter=item">{{ item }}</button>
          <button v-if="hasUnclassified" :class="{active:subjectFilter==='__unclassified__'}" @click="subjectFilter='__unclassified__'">历史未分类</button>
        </div>
        <div class="table-row head"><span>知识点</span><span>掌握度</span><span>学习状态</span><span>答题统计</span><span>最近学习</span><span></span></div>
        <div v-for="item in masteries" :key="item.knowledge_point_id" class="table-row">
          <span><b>{{ item.knowledge_point_name }}</b></span><span><div class="knowledge-progress"><i :style="{width:item.mastery_score+'%'}"></i></div><b>{{ item.mastery_score }}%</b><small :title="item.evidence_text">{{ confidenceLabel(item.evaluation_confidence) }}</small></span>
          <span><em :class="statusClass(item.learning_status)">{{ statusLabel(item.learning_status) }}</em></span><span>{{ item.correct_count }} / {{ item.answer_count }}</span><span>{{ formatDate(item.last_studied_at) }}</span><div class="row-actions"><button type="button" @click.stop="review(item)">先复习</button><button type="button" @click.stop="emit('practice', item.knowledge_point_name)">去练习</button></div>
        </div>
        <div v-if="!masteries.length" class="state-box">暂无相关知识点，完成首次诊断或练习后会显示在这里。</div>
      </article>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getMasteries, getMasteryTrend } from '../api/mastery'
import { subjectsForStage } from '../constants/education'

const props = defineProps({ profile: { type: Object, default: null }, username: { type: String, default: '同学' } })
const emit = defineEmits(['edit', 'practice', 'review'])
const loading = ref(true)
const allMasteries = ref([])
const responseSubjects = ref([])
const subjectFilter = ref('')
const hasUnclassified = ref(false)
const subjectOptions = computed(() => props.profile?.stage === 'university'
  ? responseSubjects.value
  : [...new Set([...subjectsForStage(props.profile?.stage), ...responseSubjects.value])])
const masteries = computed(() => allMasteries.value.filter(item => {
  if (!subjectFilter.value) return true
  if (subjectFilter.value === '__unclassified__') return !item.subject
  return item.subject === subjectFilter.value
}))
const total = ref(0)
const filter = ref('')
const trendDays = 7
const trend = ref({ current_score: 0, change: 0, points: [] })
const filters = [{ value: '', label: '全部' }, { value: 'weak', label: '薄弱' }, { value: 'consolidating', label: '巩固中' }, { value: 'mastered', label: '已掌握' }]
const stageLabels = { primary: '小学', junior: '初中', senior: '高中', university: '大学' }
const initial = computed(() => props.username?.slice(0, 1).toUpperCase() || '学')
const profileText = computed(() => props.profile ? `${stageLabels[props.profile.stage] || props.profile.stage} · ${props.profile.grade} · ${props.profile.subject}` : '尚未完善学习信息')
const statusText = computed(() => trend.value.current_score < 60 ? '基础仍需加强' : trend.value.current_score <= 80 ? '正在稳步提升' : '整体掌握良好')

onMounted(load)
async function load() {
  loading.value = true
  try {
    const [itemsResult, trendResult] = await Promise.allSettled([
      getMasteries({ page_size: 100, status: filter.value || undefined }),
      getMasteryTrend(trendDays),
    ])

    if (itemsResult.status === 'fulfilled') {
      allMasteries.value = itemsResult.value.data.items || []
      total.value = itemsResult.value.data.total || 0
      responseSubjects.value = itemsResult.value.data.subjects || []
      hasUnclassified.value = Boolean(itemsResult.value.data.has_unclassified)
    }
    if (trendResult.status === 'fulfilled') {
      trend.value = trendResult.value.data || trend.value
    }

    const failures = [itemsResult, trendResult].filter(result => result.status === 'rejected')
    if (failures.length === 2) {
      ElMessage.error(failures[0].reason?.message || '学习画像加载失败')
    } else if (failures.length === 1) {
      ElMessage.warning('部分学习画像数据加载失败，请稍后刷新')
    }
  } finally { loading.value = false }
}
async function setFilter(value) { filter.value = value; await load() }
function statusLabel(value) { return { weak: '基础薄弱', consolidating: '正在巩固', mastered: '掌握良好' }[value] || value }
function statusClass(value) { return { weak: 'weak', consolidating: 'medium', mastered: 'good' }[value] || '' }
function confidenceLabel(value) { return { low: '证据不足', medium: '可信度中等', high: '评估较稳定' }[value] || '证据不足' }
function formatDate(value) { return value ? new Date(value).toLocaleDateString() : '暂无' }
function review(item) {
  emit('review', {
    name: item.knowledge_point_name,
    subject: item.subject || props.profile?.subject || '',
    from: 'profile',
  })
}
</script>

<style scoped>
.state-box{padding:42px;text-align:center;color:#8490a2}.empty-small{padding:45px;text-align:center;color:#a0aaba}.row-actions{display:flex;gap:6px}.row-actions button{padding:5px 8px;border:0;border-radius:7px;color:#356fe6;background:#fff;white-space:nowrap}.row-actions button:first-child{background:#edf4ff}.table-row>span:nth-child(2) small{grid-column:1/-1;margin-top:2px;color:#9a6b22;font-size:10px}.subject-tabs{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:16px 0 6px;padding:10px 12px;border-radius:9px;background:#f7f9fc}.subject-tabs span{margin-right:3px;color:#7c899b;font-size:10px}.subject-tabs button{padding:6px 12px;border:1px solid transparent;border-radius:15px;color:#657287;background:#fff;font-size:9px}.subject-tabs button.active{color:#fff;background:#356fe6}
</style>
