/** 成员四：学习记录、推荐、每日计划、站内提醒 API */

import { request } from '../api'

/** 获取历史学习记录 */
export function getRecords(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page)
  if (params.page_size) query.set('page_size', params.page_size)
  if (params.type) query.set('type', params.type)
  if (params.subject) query.set('subject', params.subject)
  if (params.date_from) query.set('date_from', params.date_from)
  if (params.date_to) query.set('date_to', params.date_to)
  const qs = query.toString()
  return request(`/records${qs ? '?' + qs : ''}`, { auth: true })
}

/** 获取学习记录统计摘要 */
export function getRecordsStats() {
  return request('/records/stats', { auth: true })
}

/** 获取首页推荐 */
export function getHomeRecommendations() {
  return request('/recommendations/home', { auth: true })
}

/** 获取今日计划 */
export function getTodayPlan() {
  return request('/plans/today', { auth: true })
}

/** 获取站内提醒 */
export function getNotifications(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page)
  if (params.page_size) query.set('page_size', params.page_size)
  const qs = query.toString()
  return request(`/notifications${qs ? '?' + qs : ''}`, { auth: true })
}

/** 获取未读通知数量 */
export function getUnreadCount() {
  return request('/notifications/unread-count', { auth: true })
}

/** 标记提醒已读 */
export function markNotificationRead(notificationId) {
  return request(`/notifications/${notificationId}/read`, {
    method: 'POST',
    auth: true,
  })
}

/** 批量标记所有通知已读 */
export function markAllNotificationsRead() {
  return request('/notifications/read-all', {
    method: 'POST',
    auth: true,
  })
}
