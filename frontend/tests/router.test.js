import { describe, expect, it } from 'vitest'
import router from '../src/router'

describe('application routes', () => {
  it('maps every business view to a refreshable URL', () => {
    const names = router.getRoutes().map(route => route.name)
    expect(names).toEqual(expect.arrayContaining([
      'home', 'learn', 'profile', 'mistakes', 'records',
      'reports', 'points', 'vip', 'settings', 'payment-result',
    ]))
  })
})
