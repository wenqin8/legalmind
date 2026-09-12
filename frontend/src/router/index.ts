import { createRouter, createWebHistory } from 'vue-router'

import { readAccessToken } from '@/api/client'
import AuthView from '@/views/AuthView.vue'
import ChatView from '@/views/ChatView.vue'
import HomeView from '@/views/HomeView.vue'
import NotFoundView from '@/views/NotFoundView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/auth',
      name: 'auth',
      component: AuthView,
    },
    {
      path: '/chat',
      name: 'chat',
      component: ChatView,
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundView,
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const hasToken = readAccessToken() !== null
  if (to.meta.requiresAuth && !hasToken) {
    return { name: 'auth', query: { redirect: to.fullPath } }
  }

  if (to.name === 'auth' && hasToken) {
    const requestedRedirect = to.query.redirect
    const destination =
      typeof requestedRedirect === 'string' &&
      requestedRedirect.startsWith('/') &&
      !requestedRedirect.startsWith('//')
        ? requestedRedirect
        : '/chat'
    return destination
  }

  return true
})

export default router
