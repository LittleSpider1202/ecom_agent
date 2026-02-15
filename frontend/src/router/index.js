import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页' },
    children: [
      {
        path: 'task/:type',
        name: 'TaskConfig',
        component: () => import('@/views/TaskConfig.vue'),
        meta: { title: '任务配置' }
      }
    ]
  },
  {
    path: '/task/:type/detail/:id',
    name: 'TaskDetail',
    component: () => import('@/views/TaskDetail.vue'),
    meta: { title: '任务详情' }
  },
  {
    path: '/manager',
    name: 'Manager',
    component: () => import('@/views/Manager.vue'),
    meta: { title: '任务流程管理' }
  },
  {
    path: '/executor',
    name: 'Executor',
    component: () => import('@/views/Executor.vue'),
    meta: { title: '我的任务' }
  },
  {
    path: '/storage',
    name: 'Storage',
    component: () => import('@/views/Storage.vue'),
    meta: { title: '存储管理' }
  },
  {
    path: '/workers',
    name: 'Workers',
    component: () => import('@/views/Workers.vue'),
    meta: { title: 'Worker 管理' }
  },
  {
    path: '/marketplace',
    name: 'Marketplace',
    component: () => import('@/views/Marketplace.vue'),
    meta: { title: '脚本市场' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '商家工作台plus'} - 商家工作台plus`
  next()
})

export default router
