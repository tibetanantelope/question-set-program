/** 成员四：学情报告 API */

import { request } from '../api'

const newRequestId = () => globalThis.crypto?.randomUUID?.()
  || `${Date.now()}-${Math.random().toString(16).slice(2)}`

/** 生成阶段性学情报告 */
export function generateStageReport({ date_from, date_to, payment_method }, requestId) {
  return request('/reports/stage', {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': requestId || newRequestId() },
    body: { date_from, date_to, payment_method },
  })
}

/** 获取历史报告列表 */
export function getReports(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page)
  if (params.page_size) query.set('page_size', params.page_size)
  const qs = query.toString()
  return request(`/reports${qs ? '?' + qs : ''}`, { auth: true })
}

/** 获取单份报告详情 */
export function getReportDetail(reportId) {
  return request(`/reports/${reportId}`, { auth: true })
}
