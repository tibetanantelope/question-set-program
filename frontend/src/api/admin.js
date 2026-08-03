import { request, getToken } from '../api.js'

// ---------------------------------------------------------------
// 管理员 API
// ---------------------------------------------------------------

/** 用户列表（搜索/筛选/分页） */
export function listUsers({ keyword, role, status, page = 1, pageSize = 20 } = {}) {
  const params = new URLSearchParams()
  if (keyword) params.set('keyword', keyword)
  if (role) params.set('role', role)
  if (status) params.set('status', status)
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  return request(`/admin/users?${params}`, { auth: true })
}

/** 用户详情 */
export function getUserDetail(userId) {
  return request(`/admin/users/${userId}`, { auth: true })
}

/** 禁用用户 */
export function disableUser(userId) {
  return request(`/admin/users/${userId}/disable`, { method: 'POST', auth: true })
}

/** 恢复用户 */
export function restoreUser(userId) {
  return request(`/admin/users/${userId}/restore`, { method: 'POST', auth: true })
}

/** 操作审计日志 */
export function listAudits({ adminId, action, page = 1, pageSize = 20 } = {}) {
  const params = new URLSearchParams()
  if (adminId) params.set('admin_id', String(adminId))
  if (action) params.set('action', action)
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  return request(`/admin/audits?${params}`, { auth: true })
}
