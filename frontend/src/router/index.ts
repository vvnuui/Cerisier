import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  // Blog public routes
  {
    path: '/',
    component: () => import('@/layouts/BlogLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('@/views/blog/HomePage.vue') },
      { path: 'posts', name: 'posts', component: () => import('@/views/blog/PostListPage.vue') },
      { path: 'post/:slug', name: 'post-detail', component: () => import('@/views/blog/PostDetailPage.vue') },
      { path: 'categories', name: 'categories', component: () => import('@/views/blog/CategoriesPage.vue') },
      { path: 'tags', name: 'tags', component: () => import('@/views/blog/TagsPage.vue') },
      { path: 'archives', name: 'archives', component: () => import('@/views/blog/ArchivesPage.vue') },
      { path: 'about', name: 'about', component: () => import('@/views/blog/AboutPage.vue') },
    ],
  },
  // Admin routes
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'login', name: 'admin-login', component: () => import('@/views/admin/LoginPage.vue') },
      { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/views/admin/DashboardPage.vue') },
      { path: 'posts', name: 'admin-posts', component: () => import('@/views/admin/PostListPage.vue') },
      { path: 'posts/edit/:id?', name: 'admin-post-edit', component: () => import('@/views/admin/PostEditPage.vue') },
      { path: 'comments', name: 'admin-comments', component: () => import('@/views/admin/CommentPage.vue') },
      { path: 'categories', name: 'admin-categories', component: () => import('@/views/admin/CategoryPage.vue') },
      { path: 'tags', name: 'admin-tags', component: () => import('@/views/admin/TagPage.vue') },
      { path: 'settings', name: 'admin-settings', component: () => import('@/views/admin/SettingsPage.vue') },
      // Quant routes
      { path: 'quant', redirect: '/admin/quant/dashboard' },
      { path: 'quant/dashboard', name: 'quant-dashboard', component: () => import('@/views/admin/quant/DashboardPage.vue') },
      { path: 'quant/picks', name: 'quant-picks', component: () => import('@/views/admin/quant/PicksPage.vue') },
      { path: 'quant/stock/:code', name: 'quant-stock', component: () => import('@/views/admin/quant/StockAnalysisPage.vue') },
      { path: 'quant/kline/:code', name: 'quant-kline', component: () => import('@/views/admin/quant/KlineWorkbench.vue') },
      { path: 'quant/simulator', name: 'quant-simulator', component: () => import('@/views/admin/quant/SimulatorPage.vue') },
      { path: 'quant/reports', name: 'quant-reports', component: () => import('@/views/admin/quant/ReportsPage.vue') },
      { path: 'quant/settings', name: 'quant-settings', component: () => import('@/views/admin/quant/SettingsPage.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
