<template>
  <div class="admin-page">
    <div class="admin-topbar">
      <h1>智学伴 · 管理员</h1>
      <div>
        <span class="admin-user">admin01</span>
        <button class="logout-btn" @click="$emit('logout')">退出</button>
      </div>
    </div>

    <div class="admin-tabs">
      <button :class="{ active: tab === 'overview' }" @click="tab = 'overview'">运营总览</button>
      <button :class="{ active: tab === 'users' }" @click="tab = 'users'; ensureUsers()">用户管理</button>
      <button :class="{ active: tab === 'audits' }" @click="tab = 'audits'; loadAudits()">操作日志</button>
    </div>

    <!-- 运营总览 -->
    <div v-if="tab === 'overview'" class="admin-section">
      <div class="admin-toolbar">
        <label class="range-label">统计窗口</label>
        <select v-model.number="rangeDays" @change="loadOverview(); loadTrend()">
          <option :value="7">近 7 天</option>
          <option :value="30">近 30 天</option>
        </select>
        <button @click="loadOverview(); loadTrend(); loadSubjects()">刷新</button>
      </div>

      <div v-if="overviewLoading" class="loading-msg">加载中…</div>
      <div v-else-if="overviewError" class="error-box">
        <p>{{ overviewError }}</p>
        <button @click="loadOverview()">重试</button>
      </div>
      <template v-else-if="overview">
        <!-- 统计卡片 -->
        <div class="stat-cards">
          <div class="stat-card">
            <small>总用户数</small>
            <strong>{{ overview.user_stats.total_users }}</strong>
            <span>普通用户账号</span>
          </div>
          <div class="stat-card">
            <small>活跃用户</small>
            <strong>{{ overview.user_stats.active_users }}</strong>
            <span>近 {{ overview.days }} 天有学习</span>
          </div>
          <div class="stat-card">
            <small>新增用户</small>
            <strong>{{ overview.user_stats.new_users }}</strong>
            <span>近 {{ overview.days }} 天首次学习</span>
          </div>
          <div class="stat-card">
            <small>练习总次数</small>
            <strong>{{ overview.practice_stats.practice_total }}</strong>
            <span>已完成 {{ overview.practice_stats.practice_completed }}</span>
          </div>
          <div class="stat-card">
            <small>练习完成率</small>
            <strong :class="rateClass(overview.practice_stats.completion_rate)">{{ overview.practice_stats.completion_rate }}%</strong>
            <span>完成 / 总数</span>
          </div>
          <div class="stat-card">
            <small>平均正确率</small>
            <strong :class="rateClass(overview.practice_stats.avg_accuracy)">{{ overview.practice_stats.avg_accuracy }}%</strong>
            <span>仅统计已完成练习</span>
          </div>
          <div class="stat-card">
            <small>错题总数</small>
            <strong>{{ overview.mistake_stats.mistake_total }}</strong>
            <span>复习 {{ overview.mistake_stats.review_completed }} / {{ overview.mistake_stats.review_total }}</span>
          </div>
          <div class="stat-card">
            <small>复习完成率</small>
            <strong :class="rateClass(overview.mistake_stats.review_completion_rate)">{{ overview.mistake_stats.review_completion_rate }}%</strong>
            <span>已完成 / 复习计划</span>
          </div>
        </div>

        <!-- 掌握度分布 -->
        <div class="dash-panel">
          <h3>知识点掌握度分布</h3>
          <div v-if="masteryTotal === 0" class="loading-msg">暂无掌握度数据</div>
          <div v-else class="dist-bars">
            <div v-for="d in overview.mastery_distribution" :key="d.status" class="dist-row">
              <span class="dist-label">{{ d.label }}</span>
              <div class="dist-track">
                <i :class="'dist-' + d.status" :style="{ width: distPercent(d.count) + '%' }"></i>
              </div>
              <span class="dist-value">{{ d.count }}（{{ distPercent(d.count) }}%）</span>
            </div>
          </div>
        </div>

        <!-- 近 N 天趋势 -->
        <div class="dash-panel">
          <h3>近 {{ rangeDays }} 天学习活跃趋势</h3>
          <div v-if="trendLoading" class="loading-msg">加载中…</div>
          <div v-else-if="trendMax === 0" class="loading-msg">该时间范围内暂无学习记录</div>
          <div v-else class="trend-chart">
            <div v-for="p in trend.points" :key="p.date" class="trend-col" :title="`${p.date}｜练习 ${p.record_count}｜活跃 ${p.active_users}`">
              <div class="trend-bar">
                <i :style="{ height: trendHeight(p.record_count) + '%' }"></i>
              </div>
              <small>{{ p.date.slice(5) }}</small>
            </div>
          </div>
        </div>

        <!-- 学科分布 -->
        <div class="dash-panel">
          <h3>学科练习分布</h3>
          <div v-if="subjectsLoading" class="loading-msg">加载中…</div>
          <div v-else-if="!subjects.length" class="loading-msg">暂无学科数据</div>
          <table v-else class="admin-table">
            <thead>
              <tr><th>学科</th><th>练习次数</th><th>平均正确率</th></tr>
            </thead>
            <tbody>
              <tr v-for="s in subjects" :key="s.subject">
                <td>{{ s.subject }}</td>
                <td>{{ s.practice_count }}</td>
                <td><span :class="'tag ' + (s.avg_accuracy >= 60 ? 'active' : 'disabled')">{{ s.avg_accuracy }}%</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <!-- 用户管理 -->
    <div v-if="tab === 'users'" class="admin-section">
      <div class="admin-toolbar">
        <input v-model="searchKeyword" placeholder="搜索用户名或ID..." @keyup.enter="searchUsers">
        <select v-model="filterStatus">
          <option value="">全部状态</option>
          <option value="active">正常</option>
          <option value="disabled">已禁用</option>
        </select>
        <select v-model="filterRole">
          <option value="">全部角色</option>
          <option value="user">普通用户</option>
          <option value="admin">管理员</option>
        </select>
        <button @click="searchUsers">搜索</button>
      </div>

      <table class="admin-table">
        <thead>
          <tr>
            <th>ID</th><th>用户名</th><th>角色</th><th>状态</th><th>年级</th><th>学科</th><th>诊断</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="usersLoading"><td colspan="8" class="loading-msg">加载中…</td></tr>
          <tr v-else-if="users.length === 0"><td colspan="8" class="loading-msg">暂无数据</td></tr>
          <tr v-for="u in users" :key="u.id" :class="{ disabled: u.status === 'disabled' }">
            <td>{{ u.id }}</td>
            <td><strong>{{ u.username }}</strong></td>
            <td><span :class="u.role === 'admin' ? 'tag admin' : 'tag'">{{ u.role === 'admin' ? '管理员' : '用户' }}</span></td>
            <td><span :class="u.status === 'active' ? 'tag active' : 'tag disabled'">{{ u.status === 'active' ? '正常' : '已禁用' }}</span></td>
            <td>{{ u.grade || '-' }}</td>
            <td>{{ u.subject || '-' }}</td>
            <td>{{ u.diagnostic_status || '-' }}</td>
            <td class="actions">
              <button v-if="u.role !== 'admin'" @click="toggleStatus(u)" :class="u.status === 'active' ? 'warn-btn' : 'ok-btn'">
                {{ u.status === 'active' ? '禁用' : '恢复' }}
              </button>
              <button @click="viewUser(u)">详情</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="pagination" v-if="totalPages > 1">
        <button :disabled="page <= 1" @click="page--; loadUsers()">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button :disabled="page >= totalPages" @click="page++; loadUsers()">下一页</button>
      </div>
    </div>

    <!-- 操作日志 -->
    <div v-if="tab === 'audits'" class="admin-section">
      <table class="admin-table">
        <thead>
          <tr><th>ID</th><th>管理员</th><th>操作</th><th>对象</th><th>时间</th></tr>
        </thead>
        <tbody>
          <tr v-if="auditsLoading"><td colspan="5" class="loading-msg">加载中…</td></tr>
          <tr v-else-if="audits.length === 0"><td colspan="5" class="loading-msg">暂无日志</td></tr>
          <tr v-for="a in audits" :key="a.id">
            <td>{{ a.id }}</td>
            <td>{{ a.admin_username }}</td>
            <td><span class="tag">{{ actionLabel(a.action) }}</span></td>
            <td>{{ a.target_type }}#{{ a.target_id }}</td>
            <td>{{ formatTime(a.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 用户详情弹窗 -->
    <div v-if="detailUser" class="modal-overlay" @click.self="detailUser = null">
      <div class="modal">
        <h3>用户详情</h3>
        <div class="detail-grid">
          <div><label>ID</label><span>{{ detailUser.id }}</span></div>
          <div><label>用户名</label><span>{{ detailUser.username }}</span></div>
          <div><label>角色</label><span>{{ detailUser.role }}</span></div>
          <div><label>状态</label><span>{{ detailUser.status }}</span></div>
          <div><label>学段</label><span>{{ detailUser.stage || '-' }}</span></div>
          <div><label>年级</label><span>{{ detailUser.grade || '-' }}</span></div>
          <div><label>学科</label><span>{{ detailUser.subject || '-' }}</span></div>
          <div><label>诊断</label><span>{{ detailUser.diagnostic_status || '-' }}</span></div>
        </div>
        <button @click="detailUser = null" class="close-btn">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, defineEmits } from 'vue'
import { listUsers, disableUser, restoreUser, getUserDetail, listAudits } from '../api/admin.js'
import { getDashboardOverview, getDashboardSubjects, getDashboardTrend } from '../api/dashboard.js'

defineEmits(['logout'])

const tab = ref('overview')

/* ---------- 运营总览 ---------- */
const rangeDays = ref(7)
const overview = ref(null)
const overviewLoading = ref(false)
const overviewError = ref('')
const subjects = ref([])
const subjectsLoading = ref(false)
const trend = ref({ points: [] })
const trendLoading = ref(false)

const masteryTotal = computed(() =>
  (overview.value?.mastery_distribution || []).reduce((s, d) => s + d.count, 0)
)
const trendMax = computed(() =>
  (trend.value.points || []).reduce((m, p) => Math.max(m, p.record_count), 0)
)

const rateClass = (v) => (v >= 80 ? 'rate-high' : v >= 50 ? 'rate-mid' : 'rate-low')
const distPercent = (count) =>
  masteryTotal.value === 0 ? 0 : Math.round((count / masteryTotal.value) * 100)
const trendHeight = (count) =>
  trendMax.value === 0 ? 0 : Math.round((count / trendMax.value) * 100)

async function loadOverview() {
  overviewLoading.value = true
  overviewError.value = ''
  try {
    const resp = await getDashboardOverview(rangeDays.value)
    overview.value = resp.data
  } catch (e) {
    overviewError.value = e?.message || '加载运营总览失败，请稍后重试'
  } finally {
    overviewLoading.value = false
  }
}

async function loadSubjects() {
  subjectsLoading.value = true
  try {
    const resp = await getDashboardSubjects()
    subjects.value = resp.data.items || []
  } catch (e) {
    console.error(e)
    subjects.value = []
  } finally {
    subjectsLoading.value = false
  }
}

async function loadTrend() {
  trendLoading.value = true
  try {
    const resp = await getDashboardTrend(rangeDays.value)
    trend.value = resp.data || { points: [] }
  } catch (e) {
    console.error(e)
    trend.value = { points: [] }
  } finally {
    trendLoading.value = false
  }
}

let usersLoaded = false
function ensureUsers() {
  if (usersLoaded) return
  usersLoaded = true
  loadUsers()
}
const searchKeyword = ref('')
const filterStatus = ref('')
const filterRole = ref('')
const users = ref([])
const usersLoading = ref(false)
const page = ref(1)
const totalPages = ref(1)
const audits = ref([])
const auditsLoading = ref(false)
const detailUser = ref(null)

const actionLabel = (a) => {
  const map = { login: '登录', disable_user: '禁用用户', restore_user: '恢复用户', view_users: '查看用户', view_user_detail: '查看详情' }
  return map[a] || a
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

async function loadUsers() {
  usersLoading.value = true
  try {
    const resp = await listUsers({
      keyword: searchKeyword.value || undefined,
      role: filterRole.value || undefined,
      status: filterStatus.value || undefined,
      page: page.value,
    })
    const d = resp.data
    users.value = d.items
    totalPages.value = d.pages
  } catch (e) {
    console.error(e)
  } finally {
    usersLoading.value = false
  }
}

async function searchUsers() {
  page.value = 1
  await loadUsers()
}

async function toggleStatus(u) {
  try {
    if (u.status === 'active') {
      await disableUser(u.id)
      u.status = 'disabled'
    } else {
      await restoreUser(u.id)
      u.status = 'active'
    }
  } catch (e) {
    console.error(e)
  }
}

async function viewUser(u) {
  try {
    const resp = await getUserDetail(u.id)
    detailUser.value = { ...u, ...resp.data, ...resp.data?.profile }
  } catch (e) {
    console.error(e)
  }
}

async function loadAudits() {
  auditsLoading.value = true
  try {
    const resp = await listAudits()
    audits.value = resp.data.items
  } catch (e) {
    console.error(e)
  } finally {
    auditsLoading.value = false
  }
}

// 初始加载：默认展示运营总览
loadOverview()
loadSubjects()
loadTrend()
</script>

<style scoped>
.admin-page { max-width: 1200px; margin: 0 auto; padding: 20px; font-family: system-ui, sans-serif; }
.admin-topbar { display: flex; justify-content: space-between; align-items: center; padding-bottom: 16px; border-bottom: 1px solid #e5e5e5; margin-bottom: 16px; }
.admin-topbar h1 { margin: 0; font-size: 22px; }
.admin-user { margin-right: 12px; color: #666; }
.logout-btn { padding: 6px 14px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer; }
.admin-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.admin-tabs button { padding: 8px 20px; border: 1px solid #ddd; border-radius: 6px; background: #f5f5f5; cursor: pointer; }
.admin-tabs button.active { background: #1a73e8; color: #fff; border-color: #1a73e8; }
.admin-toolbar { display: flex; gap: 8px; margin-bottom: 16px; }
.admin-toolbar input { flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; }
.admin-toolbar select { padding: 8px; border: 1px solid #ddd; border-radius: 6px; }
.admin-toolbar button { padding: 8px 16px; background: #1a73e8; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
.admin-table { width: 100%; border-collapse: collapse; }
.admin-table th, .admin-table td { padding: 10px 12px; border-bottom: 1px solid #eee; text-align: left; font-size: 14px; }
.admin-table th { background: #f9f9f9; font-weight: 600; }
.admin-table tr.disabled { opacity: 0.6; }
.tag { padding: 2px 8px; border-radius: 4px; font-size: 12px; background: #e8e8e8; }
.tag.admin { background: #e3f2fd; color: #1565c0; }
.tag.active { background: #e8f5e9; color: #2e7d32; }
.tag.disabled { background: #ffebee; color: #c62828; }
.loading-msg { text-align: center; padding: 24px; color: #999; }
.actions { display: flex; gap: 6px; }
.actions button { padding: 4px 10px; border: 1px solid #ddd; border-radius: 4px; background: #fff; cursor: pointer; font-size: 13px; }
.warn-btn { color: #c62828; border-color: #c62828 !important; }
.ok-btn { color: #2e7d32; border-color: #2e7d32 !important; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 16px; }
.pagination button { padding: 6px 14px; border: 1px solid #ddd; border-radius: 4px; background: #fff; cursor: pointer; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 12px; padding: 24px; min-width: 400px; max-width: 600px; }
.modal h3 { margin: 0 0 16px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.detail-grid label { font-size: 12px; color: #999; display: block; }
.detail-grid span { font-weight: 500; }
.close-btn { margin-top: 16px; padding: 8px 20px; background: #1a73e8; color: #fff; border: none; border-radius: 6px; cursor: pointer; }

/* 运营总览 */
.range-label { align-self: center; color: #666; font-size: 14px; }
.error-box { text-align: center; padding: 24px; color: #c62828; }
.error-box button { margin-top: 8px; padding: 6px 16px; border: 1px solid #c62828; border-radius: 6px; background: #fff; color: #c62828; cursor: pointer; }
.stat-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.stat-card { background: #fff; border: 1px solid #eee; border-radius: 10px; padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.stat-card small { color: #999; font-size: 12px; }
.stat-card strong { font-size: 24px; font-weight: 700; color: #222; }
.stat-card span { font-size: 12px; color: #aaa; }
.stat-card strong.rate-high { color: #2e7d32; }
.stat-card strong.rate-mid { color: #ef6c00; }
.stat-card strong.rate-low { color: #c62828; }
.dash-panel { background: #fff; border: 1px solid #eee; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; }
.dash-panel h3 { margin: 0 0 14px; font-size: 16px; }
.dist-bars { display: flex; flex-direction: column; gap: 10px; }
.dist-row { display: flex; align-items: center; gap: 12px; }
.dist-label { width: 72px; font-size: 13px; color: #555; }
.dist-track { flex: 1; height: 14px; background: #f0f0f0; border-radius: 7px; overflow: hidden; }
.dist-track i { display: block; height: 100%; border-radius: 7px; }
.dist-track i.dist-weak { background: #ef5350; }
.dist-track i.dist-consolidating { background: #ffa726; }
.dist-track i.dist-mastered { background: #66bb6a; }
.dist-value { width: 120px; text-align: right; font-size: 13px; color: #666; }
.trend-chart { display: flex; align-items: flex-end; gap: 6px; height: 160px; padding-top: 8px; }
.trend-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; height: 100%; }
.trend-bar { flex: 1; width: 60%; display: flex; align-items: flex-end; }
.trend-bar i { display: block; width: 100%; background: #1a73e8; border-radius: 4px 4px 0 0; min-height: 2px; }
.trend-col small { font-size: 11px; color: #999; }
@media (max-width: 900px) { .stat-cards { grid-template-columns: repeat(2, 1fr); } }
</style>
