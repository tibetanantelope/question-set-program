<template>
  <section class="view">
    <div class="panel-head page-head">
      <div><h2>学习管理</h2><p>错题统计 · 复习情况 · 薄弱知识点 · 学习轨迹</p></div>
    </div>

    <!-- 标签切换 -->
    <div class="tab-bar">
      <button :class="{ active: tab === 'mistakes' }" @click="tab = 'mistakes'">错题统计</button>
      <button :class="{ active: tab === 'reviews' }" @click="tab = 'reviews'">复习情况</button>
      <button :class="{ active: tab === 'weak' }" @click="tab = 'weak'">薄弱知识点</button>
      <button :class="{ active: tab === 'summary' }" @click="tab = 'summary'">学习轨迹</button>
    </div>

    <!-- 错题统计 -->
    <article v-if="tab === 'mistakes'" class="panel">
      <div v-if="mistakeLoading" class="empty-state">加载中…</div>
      <div v-else-if="!mistakeData.items.length" class="empty-state"><span>📝</span><p>暂无误题数据</p></div>
      <template v-else>
        <div class="table-view">
          <div class="table-row head">
            <span>用户</span><span>错题总数</span><span>已订正</span><span>待订正</span><span>订正率</span><span>主要错因</span>
          </div>
          <div v-for="item in mistakeData.items" :key="item.user_id" class="table-row">
            <span><b>{{ item.username }}</b><small>ID: {{ item.user_id }}</small></span>
            <span><b>{{ item.total_mistakes }}</b></span>
            <span class="up">{{ item.corrected_count }}</span>
            <span class="warn">{{ item.pending_count }}</span>
            <span><b :class="item.correction_rate >= 60 ? 'up' : 'warn'">{{ item.correction_rate }}%</b></span>
            <span><em>{{ item.top_error_label || '--' }}</em></span>
          </div>
        </div>
        <div v-if="mistakeData.pages > 1" class="pagination">
          <button :disabled="mistakePage <= 1" @click="loadMistakes(mistakePage - 1)">上一页</button>
          <span>{{ mistakePage }} / {{ mistakeData.pages }}</span>
          <button :disabled="mistakePage >= mistakeData.pages" @click="loadMistakes(mistakePage + 1)">下一页</button>
        </div>
      </template>
    </article>

    <!-- 复习情况 -->
    <article v-if="tab === 'reviews'" class="panel">
      <div v-if="reviewLoading" class="empty-state">加载中…</div>
      <div v-else-if="!reviewData.items.length" class="empty-state"><span>🔄</span><p>暂无复习数据</p></div>
      <template v-else>
        <div class="table-view">
          <div class="table-row head">
            <span>用户</span><span>复习总数</span><span>已完成</span><span>到期未完成</span><span>完成率</span>
          </div>
          <div v-for="item in reviewData.items" :key="item.user_id" class="table-row">
            <span><b>{{ item.username }}</b><small>ID: {{ item.user_id }}</small></span>
            <span><b>{{ item.total_reviews }}</b></span>
            <span class="up">{{ item.completed_count }}</span>
            <span class="warn">{{ item.overdue_count }}</span>
            <span><b :class="item.completion_rate >= 60 ? 'up' : 'warn'">{{ item.completion_rate }}%</b></span>
          </div>
        </div>
        <div v-if="reviewData.pages > 1" class="pagination">
          <button :disabled="reviewPage <= 1" @click="loadReviews(reviewPage - 1)">上一页</button>
          <span>{{ reviewPage }} / {{ reviewData.pages }}</span>
          <button :disabled="reviewPage >= reviewData.pages" @click="loadReviews(reviewPage + 1)">下一页</button>
        </div>
      </template>
    </article>

    <!-- 薄弱知识点 -->
    <article v-if="tab === 'weak'" class="panel">
      <div v-if="weakLoading" class="empty-state">加载中…</div>
      <div v-else-if="!weakData.items.length" class="empty-state"><span>📉</span><p>暂无明显薄弱知识点</p></div>
      <template v-else>
        <div class="table-view">
          <div class="table-row head">
            <span>用户</span><span>知识点</span><span>掌握度</span><span>答题/正确</span><span>状态</span><span>最近学习</span>
          </div>
          <div v-for="item in weakData.items" :key="`${item.user_id}-${item.knowledge_point_id}`" class="table-row">
            <span><b>{{ item.username }}</b><small>ID: {{ item.user_id }}</small></span>
            <span><b>{{ item.knowledge_point_name }}</b></span>
            <span><b class="warn">{{ item.mastery_score }}</b></span>
            <span>{{ item.correct_count }} / {{ item.answer_count }}</span>
            <span><em :class="item.learning_status === 'weak' ? 'weak' : 'medium'">{{ statusLabel(item.learning_status) }}</em></span>
            <span><small>{{ formatDate(item.last_studied_at) }}</small></span>
          </div>
        </div>
        <div v-if="weakData.pages > 1" class="pagination">
          <button :disabled="weakPage <= 1" @click="loadWeak(weakPage - 1)">上一页</button>
          <span>{{ weakPage }} / {{ weakData.pages }}</span>
          <button :disabled="weakPage >= weakData.pages" @click="loadWeak(weakPage + 1)">下一页</button>
        </div>
      </template>
    </article>

    <!-- 学习轨迹摘要 -->
    <article v-if="tab === 'summary'" class="panel">
      <div class="form-row">
        <label>用户ID：</label>
        <input v-model="summaryUserId" type="number" min="1" placeholder="输入用户ID" style="width:180px">
        <button class="primary-btn" :disabled="summaryLoading || !summaryUserId" @click="loadSummary">查看轨迹</button>
      </div>
      <div v-if="summaryError" class="empty-state" style="color:var(--red)">{{ summaryError }}</div>
      <div v-if="summaryLoading" class="empty-state">加载中…</div>
      <div v-else-if="summaryData" class="summary-detail">
        <div class="summary-section">
          <h4>用户信息</h4>
          <div class="summary-grid">
            <div><small>用户名</small><strong>{{ summaryData.user.username }}</strong></div>
            <div><small>状态</small><strong>{{ summaryData.user.is_active ? '正常' : '已禁用' }}</strong></div>
            <div><small>注册时间</small><strong>{{ formatDate(summaryData.user.registered_at) }}</strong></div>
          </div>
        </div>
        <div class="summary-section">
          <h4>错题概览</h4>
          <div class="summary-grid">
            <div><small>错题总数</small><strong>{{ summaryData.mistake_summary.total }}</strong></div>
            <div><small>已订正</small><strong class="up">{{ summaryData.mistake_summary.corrected }}</strong></div>
            <div><small>订正率</small><strong :class="summaryData.mistake_summary.correction_rate >= 60 ? 'up' : 'warn'">{{ summaryData.mistake_summary.correction_rate }}%</strong></div>
          </div>
        </div>
        <div class="summary-section">
          <h4>复习概览</h4>
          <div class="summary-grid">
            <div><small>复习总数</small><strong>{{ summaryData.review_summary.total }}</strong></div>
            <div><small>已完成</small><strong class="up">{{ summaryData.review_summary.completed }}</strong></div>
            <div><small>到期未完成</small><strong class="warn">{{ summaryData.review_summary.overdue }}</strong></div>
            <div><small>完成率</small><strong :class="summaryData.review_summary.completion_rate >= 60 ? 'up' : 'warn'">{{ summaryData.review_summary.completion_rate }}%</strong></div>
          </div>
        </div>
        <div class="summary-section">
          <h4>学习记录</h4>
          <div class="summary-grid">
            <div><small>记录总数</small><strong>{{ summaryData.learning_summary.total_records }}</strong></div>
            <div><small>报告数量</small><strong>{{ summaryData.report_summary.total_reports }}</strong></div>
            <div><small>最近活跃</small><strong>{{ formatDate(summaryData.learning_summary.last_active) }}</strong></div>
          </div>
        </div>
        <div v-if="summaryData.weak_knowledge_points.length" class="summary-section">
          <h4>薄弱知识点 TOP5</h4>
          <div class="weak-list">
            <div v-for="kp in summaryData.weak_knowledge_points" :key="kp.knowledge_point_id" class="weak-tag">
              {{ kp.knowledge_point_name }} ({{ kp.mastery_score }}%)
            </div>
          </div>
        </div>
        <div v-if="summaryData.recent_records.length" class="summary-section">
          <h4>最近学习记录</h4>
          <div v-for="rec in summaryData.recent_records.slice(0, 5)" :key="rec.record_id" class="mini-record">
            <span>{{ recordTypeLabel(rec.record_type) }}</span>
            <div><strong>{{ rec.title }}</strong><small>{{ rec.subject || '' }} · {{ formatDate(rec.occurred_at) }}</small></div>
            <b v-if="rec.accuracy != null" :class="rec.accuracy >= 80 ? 'up' : 'warn'">{{ Math.round(rec.accuracy) }}%</b>
          </div>
        </div>
      </div>
      <div v-if="!summaryData && !summaryLoading && !summaryError" class="empty-state">
        <span>🔍</span><p>输入用户ID查看学习轨迹摘要</p>
      </div>
    </article>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

const tab = ref('mistakes')
const BASE = ''

// 错题统计
const mistakeLoading = ref(false), mistakeData = ref({ items: [], pages: 0 }), mistakePage = ref(1)
// 复习情况
const reviewLoading = ref(false), reviewData = ref({ items: [], pages: 0 }), reviewPage = ref(1)
// 薄弱知识点
const weakLoading = ref(false), weakData = ref({ items: [], pages: 0 }), weakPage = ref(1)
// 学习轨迹
const summaryUserId = ref(''), summaryLoading = ref(false), summaryData = ref(null), summaryError = ref('')

onMounted(() => loadMistakes())

async function adminRequest(path) {
  const token = localStorage.getItem('question_set_access_token') || ''
  const res = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.message || `请求失败: ${res.status}`)
  }
  return res.json()
}

async function loadMistakes(page = 1) {
  mistakeLoading.value = true; mistakePage.value = page
  try {
    const res = await adminRequest(`/admin/learning/mistakes?page=${page}&page_size=20`)
    mistakeData.value = res.data
  } catch (e) { ElMessage.error(e.message) }
  finally { mistakeLoading.value = false }
}

async function loadReviews(page = 1) {
  reviewLoading.value = true; reviewPage.value = page
  try {
    const res = await adminRequest(`/admin/learning/reviews?page=${page}&page_size=20`)
    reviewData.value = res.data
  } catch (e) { ElMessage.error(e.message) }
  finally { reviewLoading.value = false }
}

async function loadWeak(page = 1) {
  weakLoading.value = true; weakPage.value = page
  try {
    const res = await adminRequest(`/admin/learning/weak-points?page=${page}&page_size=20`)
    weakData.value = res.data
  } catch (e) { ElMessage.error(e.message) }
  finally { weakLoading.value = false }
}

async function loadSummary() {
  if (!summaryUserId.value) return
  summaryLoading.value = true; summaryError.value = ''; summaryData.value = null
  try {
    const res = await adminRequest(`/admin/learning/users/${summaryUserId.value}/summary`)
    summaryData.value = res.data
  } catch (e) { summaryError.value = e.message }
  finally { summaryLoading.value = false }
}

function statusLabel(v) { return { weak: '基础薄弱', consolidating: '正在巩固', mastered: '掌握良好' }[v] || v || '--' }
function formatDate(d) { if (!d) return '--'; return d.slice(0, 10) }
function recordTypeLabel(v) { return { diagnosis: '诊', practice: '练', correction: '订', review: '复', report: '报' }[v] || v || '--' }

// 监听标签切换
const tabWatcher = ref(null)
import { watch } from 'vue'
watch(tab, (val) => {
  if (val === 'mistakes' && !mistakeData.value.items.length) loadMistakes()
  if (val === 'reviews' && !reviewData.value.items.length) loadReviews()
  if (val === 'weak' && !weakData.value.items.length) loadWeak()
})
</script>

<style scoped>
.page-head { margin-bottom: 20px }
.form-row { display: flex; align-items: center; gap: 12px; margin-bottom: 20px }
.form-row label { font-size: 13px; color: #5a697d; font-weight: 600 }
.form-row input { padding: 9px 12px; border: 1px solid #dce3ed; border-radius: 8px; outline: 0 }
.form-row input:focus { border-color: #81a6ee; box-shadow: 0 0 0 3px #edf4ff }
.table-view { width: 100% }
.table-view .table-row { display: grid; grid-template-columns: 1.3fr 0.8fr 0.8fr 0.8fr 0.8fr 1fr; align-items: center; gap: 10px; padding: 12px 8px; border-bottom: 1px solid #edf0f4; font-size: 13px }
.table-view .table-row.head { color: #8995a6; background: #f7f9fc; font-size: 11px; font-weight: 700 }
.table-view .table-row span b { display: block }
.table-view .table-row span small,.table-view .table-row span em { display: block; font-size: 9px; color: #929cad }
.table-view .table-row span em { font-style: normal; margin-top: 2px }
.summary-detail { display: flex; flex-direction: column; gap: 20px }
.summary-section { padding: 16px; border: 1px solid #edf0f4; border-radius: 10px; background: #fafbfd }
.summary-section h4 { margin: 0 0 12px; font-size: 13px; color: #3d4654 }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 14px }
.summary-grid div small { display: block; color: #929cad; font-size: 9px }
.summary-grid div strong { display: block; margin-top: 4px; font-size: 18px }
.weak-list { display: flex; gap: 8px; flex-wrap: wrap }
.mini-record { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #edf0f4 }
.mini-record > span { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 7px; color: var(--blue); background: var(--soft); font-size: 10px; font-weight: 700; flex: none }
.mini-record strong,.mini-record small { display: block }
.mini-record strong { font-size: 11px }
.mini-record small { margin-top: 3px; color: #929cad; font-size: 9px }
.mini-record b { margin-left: auto; font-size: 11px }
</style>
