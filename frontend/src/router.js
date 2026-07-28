import { createRouter, createWebHistory } from 'vue-router'

const RouteAnchor = { template: '<span style="display:none" aria-hidden="true"></span>' }

const routes = [
  { path: '/', name: 'home', component: RouteAnchor },
  { path: '/learn', name: 'learn', component: RouteAnchor },
  { path: '/profile', name: 'profile', component: RouteAnchor },
  { path: '/mistakes', name: 'mistakes', component: RouteAnchor },
  { path: '/knowledge-review', name: 'knowledge-review', component: RouteAnchor },
  { path: '/records', name: 'records', component: RouteAnchor },
  { path: '/reports', name: 'reports', component: RouteAnchor },
  { path: '/points', name: 'points', component: RouteAnchor },
  { path: '/vip', name: 'vip', component: RouteAnchor },
  { path: '/settings', name: 'settings', component: RouteAnchor },
  { path: '/payment/result', name: 'payment-result', component: RouteAnchor },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
