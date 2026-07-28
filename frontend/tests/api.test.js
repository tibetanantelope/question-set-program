import { describe, expect, it, vi } from 'vitest'
import { request, setToken } from '../src/api'

describe('API request wrapper', () => {
  it('adds the bearer token for authenticated requests', async () => {
    setToken('test-token')
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ code: 'OK', data: { value: 1 } }),
    })

    const result = await request('/profile/me', { auth: true })

    expect(result.data.value).toBe(1)
    expect(fetch).toHaveBeenCalledWith('/profile/me', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
    }))
  })

  it('clears an expired token after a 401 response', async () => {
    setToken('expired-token')
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: async () => JSON.stringify({ code: 'UNAUTHORIZED', message: '登录已过期' }),
    })

    await expect(request('/profile/me', { auth: true })).rejects.toMatchObject({
      code: 'UNAUTHORIZED',
      status: 401,
    })
    expect(localStorage.getItem('question_set_access_token')).toBeNull()
  })

  it('does not expose a plain-text backend traceback', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'Traceback (most recent call last): secret stack details',
    })

    await expect(request('/profile/me')).rejects.toMatchObject({
      message: '服务器内部错误，请稍后重试',
      status: 500,
    })
  })
})
