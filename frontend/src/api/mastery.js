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
 * 查询错题列表。
 * @param {{page?:number, page_size?:number, status?:string}} params
 */
export function getMistakes(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page)
  if (params.page_size) query.set('page_size', params.page_size)
  if (params.status) query.set('status', params.status)
  const qs = query.toString()
  return request(`/mistakes${qs ? '?' + qs : ''}`, { auth: true })
}

/**
 * 提交错题订正。
 * @param {number} mistakeId 错题ID
 * @param {string} answer 订正答案
 * @param {string} [requestId] 幂等标识
 */
export function submitCorrection(mistakeId, answer, requestId) {
  return request(`/mistakes/${mistakeId}/correction`, {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': requestId || newRequestId() },
    body: { answer }
  })
}

/**
 * 查询今日到期复习内容。
 */
export function getTodayReviews() {
  return request('/mistakes/reviews/today', { auth: true })
}

export { newRequestId }
