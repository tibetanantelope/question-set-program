import { request } from '../api.js'

// ---------------------------------------------------------------
// 成员二：智能诊断与练习生成
// ---------------------------------------------------------------

/** 生成一个 X-Request-ID（用于写操作幂等） */
function newRequestId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // 回退方案
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * 学情诊断：识别知识点、评估掌握度、给出薄弱点与练习建议。
 * @param {{input_type:string, content:string, session_id?:number}} payload
 */
export function diagnose(payload) {
  return request('/learning/diagnose', {
    method: 'POST',
    auth: true,
    body: payload
  })
}

/**
 * 创建针对性练习组（内容校验 + 自动重试 + 幂等）。
 * @param {{diagnosis_id?:number, question_count?:number}} payload
 * @param {string} [requestId] 可选，复用同一 ID 可实现幂等重试
 */
export function createPractice(payload = {}, requestId) {
  return request('/learning/practices', {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': requestId || newRequestId() },
    body: { question_count: 3, ...payload }
  })
}

/** 查询练习组（不含标准答案，仅限本人） */
export function getPractice(practiceId) {
  return request(`/learning/practices/${practiceId}`, { auth: true })
}

/**
 * 提交练习答案：返回判题、错因分类与解析。
 * @param {number} practiceId
 * @param {Array<{question_id:number, answer:string}>} answers
 * @param {string} [requestId]
 */
export function submitAnswers(practiceId, answers, requestId) {
  return request(`/learning/practices/${practiceId}/answers`, {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': requestId || newRequestId() },
    body: { answers }
  })
}

export { newRequestId }
