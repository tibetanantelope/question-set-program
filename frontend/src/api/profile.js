import { request } from '../api.js'

// ---------------------------------------------------------------
// 画像
// ---------------------------------------------------------------

/** 查询当前学生基础画像和学习计划 */
export function getMyProfile() {
  return request('/profile/me', { auth: true })
}

/** 新增或修改当前学生画像 */
export function saveMyProfile(profile) {
  return request('/profile/me', { method: 'PUT', auth: true, body: profile })
}

// ---------------------------------------------------------------
// 首次诊断
// ---------------------------------------------------------------

/** 查询是否需要首次诊断 */
export function getDiagnosticStatus() {
  return request('/profile/diagnostic/status', { auth: true })
}

/** 生成首次诊断题 */
export function startDiagnostic() {
  return request('/profile/diagnostic/start', { method: 'POST', auth: true })
}

/** 提交首次诊断并初始化掌握度 */
export function submitDiagnostic(diagnosticId, answers) {
  return request('/profile/diagnostic/submit', {
    method: 'POST',
    auth: true,
    body: { diagnostic_id: diagnosticId, answers }
  })
}

/** 跳过诊断并使用默认掌握度 */
export function skipDiagnostic() {
  return request('/profile/diagnostic/skip', { method: 'POST', auth: true })
}

// ---------------------------------------------------------------
// 掌握度
// ---------------------------------------------------------------

/** 查询当前学生最近诊断的知识点掌握度 */
export function getMyMasteries() {
  return request('/profile/masteries', { auth: true })
}

// ---------------------------------------------------------------
// 会话管理
// ---------------------------------------------------------------

/** 结束会话并清除短期记忆 */
export function clearSessionMemory(sessionId) {
  return request(`/sessions/${sessionId}/memory`, { method: 'DELETE', auth: true })
}
