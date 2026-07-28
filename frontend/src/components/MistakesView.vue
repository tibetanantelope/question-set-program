<template>
  <section class="view">
    <div class="panel-head page-head"><div><h2>错题订正与复习</h2><p>完成订正后，系统会在 1、3、7 天后安排复习。</p></div><button class="ghost-btn" @click="load">刷新</button></div>
    <div v-if="knowledgePoint" class="related-filter">
      <span>正在查看知识点「{{ knowledgePoint }}」的关联错题</span>
      <button @click="clearKnowledgePoint">查看全部错题</button>
    </div>
    <div class="two-col mistake-columns">
      <article class="panel">
        <div class="panel-head"><div><h3>历史错题</h3><p>共 {{ total }} 道</p></div><div class="filters"><button v-for="item in filters" :key="item.value" :class="{active: status === item.value}" @click="changeStatus(item.value)">{{ item.label }}</button></div></div>
        <div class="subject-filters">
          <span>{{ stage === 'university' ? '课程' : '学科' }}</span>
          <button :class="{active: subject === ''}" @click="changeSubject('')">全部</button>
          <button v-for="item in subjectOptions" :key="item" :class="{active: subject === item}" @click="changeSubject(item)">{{ item }}</button>
          <button v-if="hasUnclassified" :class="{active: subject === '__unclassified__'}" @click="changeSubject('__unclassified__')">历史未分类</button>
        </div>
        <div v-if="loading" class="empty-state">加载中…</div>
        <div v-for="item in mistakes" :key="item.mistake_id" class="mistake-card">
          <div class="mistake-title"><div><b :class="['subject-tag', {muted: !item.subject}]">{{ item.subject || '历史未分类' }}</b><span>{{ errorTypeLabel(item.error_type) }}</span></div><small>知识点：{{ item.knowledge_point_name || '待识别' }}</small></div>
          <h4 v-if="item.correction_status === 'corrected'">
            <button class="question-link" :disabled="submitting === item.mistake_id || (!isVip && pointBalance < 10)" :title="!isVip && pointBalance < 10 ? '详细解析需 10 积分' : '点击查看详细解析'" @click="unlockDetailedAnalysis(item)">
              {{ item.question_content || '题目内容暂缺' }}
            </button>
          </h4>
          <h4 v-else>{{ item.question_content || '题目内容暂缺' }}</h4>
          <p><b>原答案：</b>{{ item.user_answer || '未记录' }}</p>
          <button v-if="item.knowledge_point_name" class="knowledge-review-btn" @click="emit('review',{name:item.knowledge_point_name,subject:item.subject,from:'mistakes'})">先复习「{{ item.knowledge_point_name }}」</button>
          <p v-if="item.correction_status === 'corrected'"><b>状态：</b>已完成订正，等待后续复习</p>
          <div v-else class="correction-form">
            <input v-model.trim="answers[item.mistake_id]" placeholder="输入订正答案" @keyup.enter="correct(item)">
            <button
              :class="['primary-btn', { 'review-required': !item.review_completed }]"
              :disabled="submitting === item.mistake_id"
              :aria-disabled="!item.review_completed || !answers[item.mistake_id]"
              @click="correct(item)"
            >{{ submitting === item.mistake_id ? '提交中…' : (item.review_completed ? '提交订正' : '请先复习后订正') }}</button>
          </div>
          <div class="analysis-actions">
            <button v-if="item.correction_status !== 'corrected' && !analysisResults[item.mistake_id]" class="reveal-btn compact" :disabled="submitting === item.mistake_id" @click="showBasicAnswer(item)">
              不会，查看答案
            </button>
            <button v-if="!analysisResults[item.mistake_id] && item.correction_status !== 'corrected'" class="analysis-btn" :disabled="submitting === item.mistake_id || (!isVip && pointBalance < 10)" @click="showAnalysis(item)">
              {{ submitting === item.mistake_id ? '加载中…' : (isVip ? '查看详细解析' : pointBalance < 10 ? '积分不足（详细解析需 10）' : '10 积分兑换详细解析') }}
            </button>
          </div>
          <div v-if="analysisResults[item.mistake_id]" class="analysis-result">
            <div class="analysis-result-head"><strong>答案与解析</strong><button @click="analysisCollapsed[item.mistake_id]=!analysisCollapsed[item.mistake_id]">{{ analysisCollapsed[item.mistake_id] ? '展开' : '收起' }}</button></div>
            <template v-if="!analysisCollapsed[item.mistake_id]">
              <p><b>标准答案：</b>{{ analysisResults[item.mistake_id].standard_answer || '暂无标准答案' }}</p>
              <p><b>简单解析：</b>{{ analysisResults[item.mistake_id].simple_analysis }}</p>
            <div v-if="analysisResults[item.mistake_id].detailed_analysis">
              <p><b>详细解析：</b>{{ analysisResults[item.mistake_id].detailed_analysis }}</p>
              <small v-if="analysisResults[item.mistake_id].payment_method === 'points'" class="payment-tag">已使用 10 积分兑换</small>
              <small v-else-if="analysisResults[item.mistake_id].payment_method === 'vip'" class="payment-tag vip">VIP 权益</small>
            </div>
            <div v-else class="analysis-upgrade">
              <p>普通用户可免费查看简单解析，也可使用积分兑换详细解析；VIP 用户可直接查看详细解析。</p>
              <button class="primary-btn small" :disabled="submitting === item.mistake_id || (!isVip && pointBalance < 10)" @click="unlockDetailedAnalysis(item)">
                {{ isVip ? 'VIP 查看详细解析' : `10 积分兑换详细解析（余额 ${pointBalance}）` }}
              </button>
            </div>
            </template>
          </div>
          <div v-if="results[item.mistake_id]" :class="['correction-result', results[item.mistake_id].is_correct ? 'ok' : 'bad']">
            <strong>{{ results[item.mistake_id].is_correct ? '订正正确 ✓' : '答案仍需调整' }}</strong>
            <p v-if="results[item.mistake_id].grading_reason"><b>{{ results[item.mistake_id].grading_method === 'ai' ? 'AI 判定依据：' : '判定依据：' }}</b>{{ results[item.mistake_id].grading_reason }}</p>
            <p v-if="results[item.mistake_id].review_dates?.length">复习日期：{{ results[item.mistake_id].review_dates.join('、') }}</p>
            <p v-if="!results[item.mistake_id].is_correct">标准答案：{{ item.standard_answer || '请结合解析重新作答' }}</p>
          </div>
        </div>
        <div v-if="!loading && !mistakes.length" class="empty-state">当前没有符合条件的错题。</div>
      </article>
      <article class="panel">
        <div class="panel-head"><div><h3>今日到期复习</h3><p>优先完成到期内容</p></div><span class="priority">{{ reviews.length }} 道</span></div>
        <div v-for="item in reviews" :key="item.review_id" class="review-card">
          <small><b class="subject-tag">{{ item.subject || '未分类学科' }}</b> · {{ item.knowledge_point_name || '待识别知识点' }} · {{ item.review_date }}</small>
          <h4>{{ item.question_content || '题目内容暂缺' }}</h4>
          <p>原错误答案：{{ item.user_answer || '未记录' }}</p>
          <template v-if="!reveals[item.review_id]">
            <input v-model.trim="answers[item.mistake_id]" placeholder="再次作答">
            <div class="review-actions">
              <button class="primary-btn" :disabled="submitting === item.mistake_id || !answers[item.mistake_id]" @click="correct(item)">提交复习答案</button>
              <button class="reveal-btn" :disabled="submitting === item.mistake_id" @click="reveal(item)">不会，查看答案</button>
            </div>
          </template>
          <div v-else class="reveal-result">
            <strong>本轮已记录为"不会"，掌握度 {{ reveals[item.review_id].mastery_change }}%</strong>
            <p><b>标准答案：</b>{{ reveals[item.review_id].standard_answer || '暂无标准答案' }}</p>
            <p><b>解析：</b>{{ reveals[item.review_id].analysis }}</p>
            <small v-if="reveals[item.review_id].next_review_date">
              第 {{ reveals[item.review_id].current_round }}/{{ reveals[item.review_id].total_rounds }} 轮完成，下次复习：{{ reveals[item.review_id].next_review_date }}
            </small>
            <small v-else>三轮复习已完成；该知识点仍未掌握，建议返回智能学习进行专项巩固。</small>
          </div>
        </div>
        <div v-if="!reviews.length" class="empty-state">今天没有到期复习，保持当前学习节奏。</div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getMistakes, getTodayReviews, revealReviewAnswer, submitCorrection, getMistakeAnalysis } from '../api/mastery'
import { subjectsForStage } from '../constants/education'

const emit = defineEmits(['updated', 'review', 'clear-filter'])
const props = defineProps({
  stage: { type: String, default: '' },
  isVip: { type: Boolean, default: false },
  pointBalance: { type: Number, default: 0 },
  initialKnowledgePoint: { type: String, default: '' },
  initialStatus: { type: String, default: '' },
})
const loading = ref(true), mistakes = ref([]), reviews = ref([]), total = ref(0), status = ref(props.initialStatus), subject = ref(''), knowledgePoint = ref(props.initialKnowledgePoint), subjects = ref([]), submitting = ref(null)
const subjectOptions = computed(() => [...new Set([...subjectsForStage(props.stage), ...subjects.value])])
const hasUnclassified = ref(false)
const answers = reactive({}), results = reactive({}), reveals = reactive({})
const analysisResults = reactive({})
const analysisCollapsed = reactive({})
const filters = [{ value: '', label: '全部' }, { value: 'pending', label: '待订正' }, { value: 'corrected', label: '已订正' }, { value: 'review_due', label: '待复习' }]
onMounted(load)
async function load() {
  loading.value = true
  try {
    const [mistakePayload, reviewPayload] = await Promise.all([getMistakes({ page_size: 100, status: status.value || undefined, subject: subject.value || undefined, knowledge_point_name: knowledgePoint.value || undefined }), getTodayReviews()])
    mistakes.value = mistakePayload?.data?.items || []
    total.value = mistakePayload?.data?.total || 0
    subjects.value = mistakePayload?.data?.subjects || subjects.value
    hasUnclassified.value = Boolean(mistakePayload?.data?.has_unclassified)
    reviews.value = reviewPayload?.data || []
  } catch (error) { ElMessage.error(error.message || '错题数据加载失败') }
  finally { loading.value = false }
}
async function changeStatus(value) { status.value = value; await load() }
async function changeSubject(value) { subject.value = value; await load() }
async function clearKnowledgePoint() { knowledgePoint.value = ''; emit('clear-filter'); await load() }
async function correct(item) {
  if (!item.review_id && !item.review_completed) {
    ElMessage.warning(`请先完成「${item.knowledge_point_name || '该知识点'}」的知识点复习，再提交订正`)
    return
  }
  const answer = String(answers[item.mistake_id] || '').trim()
  if (!answer) {
    ElMessage.warning('请先输入订正答案')
    return
  }
  submitting.value = item.mistake_id
  try {
    const payload = await submitCorrection(item.mistake_id, answer, undefined, item.review_id || null)
    results[item.mistake_id] = payload.data
    if (payload.data.is_correct) {
      ElMessage.success(payload.data.first_success ? '订正成功，积分和复习计划已更新' : '复习完成')
      await load()
      emit('updated')
    } else ElMessage.warning('答案仍不正确，请查看标准答案后重试')
  } catch (error) { ElMessage.error(error.message || '订正提交失败') }
  finally { submitting.value = null }
}
async function reveal(item) {
  submitting.value = item.mistake_id
  try {
    const payload = await revealReviewAnswer(item.mistake_id, item.review_id)
    reveals[item.review_id] = payload.data
    ElMessage.info(payload.data.next_review_date ? '已记录本轮结果，请理解解析后等待下次复习' : '三轮复习已完成，建议进行专项巩固')
    emit('updated')
  } catch (error) { ElMessage.error(error.message || '答案查看失败') }
  finally { submitting.value = null }
}
async function showBasicAnswer(item) {
  if (analysisResults[item.mistake_id]) return
  submitting.value = item.mistake_id
  try {
    const payload = await getMistakeAnalysis(item.mistake_id, 'basic')
    analysisResults[item.mistake_id] = payload.data
    analysisCollapsed[item.mistake_id] = false
  } catch (error) { ElMessage.error(error.message || '答案加载失败') }
  finally { submitting.value = null }
}
async function showAnalysis(item) { await unlockDetailedAnalysis(item) }
async function unlockDetailedAnalysis(item) {
  if (analysisResults[item.mistake_id]?.detailed_analysis) return
  if (!props.isVip && props.pointBalance < 10) {
    ElMessage.warning('积分不足，请先完成学习任务获取积分')
    return
  }
  submitting.value = item.mistake_id
  try {
    const payload = await getMistakeAnalysis(item.mistake_id, props.isVip ? 'vip' : 'points')
    analysisResults[item.mistake_id] = payload.data
    analysisCollapsed[item.mistake_id] = false
    ElMessage.success(props.isVip ? '已加载 VIP 详细解析' : '已使用 10 积分兑换详细解析')
    emit('updated')
  } catch (error) {
    if (error.message?.includes('积分不足') || error.message?.includes('POINT')) {
      ElMessage.warning('积分不足，请先完成学习任务获取积分')
    } else {
      ElMessage.error(error.message || '兑换失败')
    }
  } finally { submitting.value = null }
}
function errorTypeLabel(value) { return { knowledge: '知识点不会', calculation: '计算错误', reading: '审题错误', method: '方法错误' }[value] || '待分析' }
</script>

<style scoped>
.related-filter{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;padding:12px 16px;border:1px solid #cfe0ff;border-radius:10px;color:#315fba;background:#f1f6ff}.related-filter button{padding:7px 12px;border:0;border-radius:8px;color:#356fe6;background:#fff;cursor:pointer}
.page-head{margin-bottom:20px}.mistake-columns{align-items:start}.subject-filters{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:16px 0 4px;padding:10px 12px;border-radius:9px;background:#f7f9fc}.subject-filters span{margin-right:4px;color:#7c899b;font-size:12px}.subject-filters button{padding:6px 13px;border:1px solid transparent;border-radius:16px;color:#657287;background:#fff;cursor:pointer;font-size:12px}.subject-filters button:hover{color:#356fe6;border-color:#cddcf8}.subject-filters button.active{color:#fff;background:#356fe6}.course-label-hint{margin:14px 0 4px;padding:10px 12px;border-radius:9px;color:#718096;background:#f7f9fc;font-size:12px}.mistake-card,.review-card{padding:18px 0;border-top:1px solid #edf0f4}.mistake-title{display:flex;justify-content:space-between;gap:10px}.mistake-title>div{display:flex;gap:7px;align-items:center}.mistake-title span{padding:3px 8px;border-radius:5px;color:#d66b38;background:#fff1e9}.subject-tag{display:inline-block;padding:3px 8px;border-radius:5px;color:#356fe6;background:#edf4ff;font-size:11px}.subject-tag.muted{color:#7a8494;background:#f0f2f5}.mistake-title small{color:#8490a2}.mistake-card h4,.review-card h4{margin:10px 0;line-height:1.6}.mistake-card p,.review-card p{color:#68758a;font-size:12px}.correction-form{display:flex;gap:10px}.correction-form input,.review-card input{flex:1;box-sizing:border-box;padding:10px;border:1px solid #dfe5ed;border-radius:8px}.review-card input{width:100%;margin:8px 0}.review-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px}.review-actions button{min-height:42px}.reveal-btn{border:1px solid #d6deeb;border-radius:8px;color:#52627a;background:#fff;cursor:pointer;font-weight:600}.reveal-btn:hover{color:#2f67d8;border-color:#9db8ed;background:#f6f9ff}.reveal-result{margin-top:10px;padding:14px;border:1px solid #f0d9a8;border-radius:9px;color:#76531f;background:#fff9ed}.reveal-result p{color:#664b25}.reveal-result small{display:block;margin-top:8px}.correction-result{margin-top:10px;padding:12px;border-radius:8px}.correction-result.ok{background:#eef9f2;color:#297a47}.correction-result.bad{background:#fff1f1;color:#b44343}.empty-state{padding:45px 10px;text-align:center;color:#98a3b3}
.analysis-actions{display:flex;gap:8px;margin-top:10px}
.question-link{padding:0;border:0;color:inherit;background:transparent;cursor:pointer;font:inherit;font-weight:inherit;text-align:left;line-height:inherit}
.question-link:hover{color:#356fe6;text-decoration:underline}
.question-link:disabled{opacity:.6;cursor:wait}
.reveal-btn.compact{min-height:auto;padding:8px 16px;font-size:12px}
.analysis-btn{padding:8px 16px;border:1px solid #356fe6;border-radius:8px;color:#356fe6;background:#fff;cursor:pointer;font-size:12px;font-weight:600}
.analysis-btn:hover{background:#f0f5ff}
.analysis-btn:disabled{opacity:.5;cursor:not-allowed}
.analysis-result{margin-top:12px;padding:14px;border:1px solid #e2e8f0;border-radius:9px;background:#f8fafc}
.analysis-result-head{display:flex;align-items:center;justify-content:space-between}.analysis-result-head button{padding:3px 8px;border:0;color:#356fe6;background:transparent;font-size:11px}
.analysis-result p{margin:6px 0;color:#475569;font-size:13px;line-height:1.7}
.analysis-result p b{color:#1e293b}
.analysis-upgrade{margin-top:10px;padding:12px;border:1px dashed #cbd5e1;border-radius:8px;background:#fff;text-align:center}
.analysis-upgrade p{color:#64748b;font-size:12px;margin-bottom:10px}
.payment-tag{display:inline-block;margin-top:6px;padding:2px 8px;border-radius:4px;color:#059669;background:#d1fae5;font-size:11px}
.payment-tag.vip{color:#7c3aed;background:#ede9fe}
.primary-btn.small{padding:6px 14px;font-size:12px}
.knowledge-review-btn{margin:4px 0 10px;padding:7px 12px;border:0;border-radius:8px;color:#356fe6;background:#edf4ff;font-size:11px;font-weight:600}
.primary-btn.review-required{opacity:.62;cursor:not-allowed;box-shadow:none}
</style>
