import { request } from '../api'

function requestId(prefix) {
  const id = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `${prefix}-${id}`
}

export function getPointAccount() {
  return request('/points/account', { auth: true })
}

export function getPointTransactions(page = 1, pageSize = 20) {
  return request(`/points/transactions?page=${page}&page_size=${pageSize}`, { auth: true })
}

export function getPointTasks() {
  return request('/points/tasks', { auth: true })
}

export function checkIn() {
  return request('/points/check-in', {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': requestId('daily-check-in') }
  })
}

export function exchangePoints(itemType, targetId = null) {
  return request('/points/exchanges', {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': requestId('point-exchange') },
    body: { item_type: itemType, target_id: targetId }
  })
}
