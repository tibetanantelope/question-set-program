import { request } from '../api.js'

// ---------------------------------------------------------------
// 成员二：管理员运营看板（/admin/dashboard/*，只读聚合）
// ---------------------------------------------------------------

/**
 * 运营总览卡片：用户 / 练习 / 错题复习 / 掌握度分布。
 * @param {number} [days=7] 活跃/新增用户统计窗口（1-90）
 */
export function getDashboardOverview(days = 7) {
  return request(`/admin/dashboard/overview?days=${days}`, { auth: true })
}

/** 学科分布：各学科练习次数与平均正确率。 */
export function getDashboardSubjects() {
  return request('/admin/dashboard/subjects', { auth: true })
}

/**
 * 近 N 天学习活跃趋势（缺失日期已由后端补零）。
 * @param {number} [days=7] 趋势统计天数（1-90）
 */
export function getDashboardTrend(days = 7) {
  return request(`/admin/dashboard/trend?days=${days}`, { auth: true })
}
