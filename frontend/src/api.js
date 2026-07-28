const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const TOKEN_KEY = 'question_set_access_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
    return
  }
  localStorage.removeItem(TOKEN_KEY)
}

async function parseJsonResponse(response) {
  const text = await response.text()
  let payload = null

  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      // Do not render an upstream HTML/plain-text traceback in the application UI.
      payload = null
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      setToken('')
    }
    const fallbackMessages = {
      500: '服务器内部错误，请稍后重试',
      502: '后端服务暂时不可用，请稍后重试',
      503: '数据库或依赖服务暂时不可用，请稍后重试',
      504: '后端服务响应超时，请稍后重试'
    }
    const message = payload?.message || payload?.detail || payload?.msg
      || fallbackMessages[response.status] || `请求失败：${response.status}`
    const error = new Error(message)
    error.code = payload?.code || `HTTP_${response.status}`
    error.status = response.status
    error.data = payload?.data
    throw error
  }

  return payload
}

export async function login(username, password) {
  const payload = await request('/login/login', {
    method: 'POST',
    body: { username, password }
  })

  if (payload?.access_token) {
    setToken(payload.access_token)
  }

  return payload
}

export async function register(username, password) {
  return request('/login/register', {
    method: 'POST',
    body: { username, password }
  })
}

export async function analyse({ userId, sessionId, text }) {
  return request('/agent/analyse', {
    method: 'POST',
    auth: true,
    body: {
      id: Number(userId),
      user_id: Number(userId),
      session_id: Number(sessionId),
      text
    }
  })
}

export async function analyseStream({ userId, sessionId, text, onEvent }) {
  const token = getToken()
  if (!token) {
    throw new Error('请先登录')
  }

  const response = await fetch(`${API_BASE_URL}/agent/analyse/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      id: Number(userId),
      user_id: Number(userId),
      session_id: Number(sessionId),
      text
    })
  })

  if (!response.ok || !response.body) {
    await parseJsonResponse(response)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''

    for (const block of blocks) {
      const line = block
        .split('\n')
        .map((item) => item.trim())
        .find((item) => item.startsWith('data:'))

      if (!line) continue

      const raw = line.replace(/^data:\s*/, '')
      if (raw === '[DONE]') {
        onEvent?.({ type: 'done' })
        continue
      }

      try {
        onEvent?.(JSON.parse(raw))
      } catch {
        onEvent?.({ type: 'raw', content: raw })
      }
    }
  }
}

export async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  }

  if (options.auth) {
    const token = getToken()
    if (!token) {
      throw new Error('请先登录')
    }
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined
  })

  return parseJsonResponse(response)
}
