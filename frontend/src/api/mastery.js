import { request } from '../api.js'

// ---------------------------------------------------------------
// 成员三：掌握度、错题订正与复习
// ---------------------------------------------------------------

/** 生成一个 X-Request-ID（用于写操作幂等） */
function newRequestId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * 查询知识点掌握情况。
 * @param {{page?:number, page_size?:number, status?:string}} params
 */
export function getMasteries(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page)
  if (params.page_size) query.set('page_size', params.page_size)
  if (params.status) query.set('status', params.status)
  const qs = query.toString()
  return request(`/mastery/knowledge-points${qs ? '?' + qs : ''}`, { auth: true })
}

/**
 * 查询掌握度变化趋势。
 * @param {number} [days=7] 统计天数
 */
export function getMasteryTrend(days = 7) {
  return request(`/mastery/trend?days=${days}`, { auth: true })
}

/**
 * 查询当前用户的学情摘要（首页学习概览）。
 * @param {number} [weakLimit=5] 薄弱知识点返回数量
 */
export function getLearningSummary(weakLimit = 5) {
  return request(`/mastery/summary?weak_limit=${weakLimit}`, { auth: true })
}

/** 获取个性化知识点复习卡。 */
export function getKnowledgeReviewCard(knowledgePointName, subject, mode = 'full') {
  const query = new URLSearchParams({ knowledge_point_name: knowledgePointName, mode })
  if (subject) query.set('subject', subject)
  return request(`/knowledge-reviews/card?${query}`, { auth: true })
}

/** 提交概念自测并记录复习。 */
export function completeKnowledgeReview(body, requestId) {
  return request('/knowledge-reviews/complete', {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': requestId || newRequestId() },
    body,
  })
}

/**
 * 查询错题列表。
 * @param {{page?:number, page_size?:number, status?:string, subject?:string, knowledge_point_name?:string}} params
 */
export function getMistakes(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page)
  if (params.page_size) query.set('page_size', params.page_size)
  if (params.status) query.set('status', params.status)
  if (params.subject) query.set('subject', params.subject)
  if (params.knowledge_point_name) query.set('knowledge_point_name', params.knowledge_point_name)
  const qs = query.toString()
  return request(`/mistakes${qs ? '?' + qs : ''}`, { auth: true })
}

/**
 * 提交错题订正。
 * @param {number} mistakeId 错题ID
 * @param {string} answer 订正答案
 * @param {string} [requestId] 幂等标识
 */
export function submitCorrection(mistakeId, answer, requestId, reviewId = null) {
  return request(`/mistakes/${mistakeId}/correction`, {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': requestId || newRequestId() },
    body: { answer, ...(reviewId ? { review_id: reviewId } : {}) }
  })
}

/**
 * 查询今日到期复习内容。
 */
export function getTodayReviews() {
  return request('/mistakes/reviews/today', { auth: true })
}

/** 本轮不会：记录结果并返回标准答案、解析和下一轮日期。 */
export function revealReviewAnswer(mistakeId, reviewId) {
  return request(`/mistakes/${mistakeId}/reviews/${reviewId}/reveal`, {
    method: 'POST',
    auth: true,
  })
}

/** 查看错题解析：VIP 直接查看详细解析；普通用户可积分兑换或仅查看简单解析。 */
export function getMistakeAnalysis(mistakeId, paymentMethod = 'basic') {
  return request(`/mistakes/${mistakeId}/analysis`, {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': newRequestId() },
    body: { payment_method: paymentMethod },
  })
}

export { newRequestId }
