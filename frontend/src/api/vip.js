import { request } from '../api'

function requestId(prefix) {
  const id = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `${prefix}-${id}`
}

export async function getVipStatus() {
  return request('/vip/status', { auth: true })
}

export async function getVipUsage() {
  return request('/vip/usage', { auth: true })
}

export async function createVipOrder() {
  return request('/vip/orders', {
    method: 'POST',
    auth: true,
    headers: { 'X-Request-ID': requestId('vip-order') },
    body: { plan: 'vip_30_days' }
  })
}

export async function createAlipayForm(orderNo) {
  return request(`/vip/orders/${encodeURIComponent(orderNo)}/alipay`, {
    method: 'POST',
    auth: true
  })
}

export async function queryVipOrder(orderNo) {
  return request(`/vip/orders/${encodeURIComponent(orderNo)}/query`, {
    method: 'POST',
    auth: true
  })
}

export async function getVipOrder(orderNo) {
  return request(`/vip/orders/${encodeURIComponent(orderNo)}`, { auth: true })
}

export async function getVipOrders(page = 1, pageSize = 20) {
  return request(`/vip/orders?page=${page}&page_size=${pageSize}`, { auth: true })
}
