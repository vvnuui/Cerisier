<template>
  <el-container class="admin-layout">
    <!-- Sidebar -->
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="admin-sidebar">
      <div class="sidebar-header">
        <span v-if="!isCollapsed" class="sidebar-title">Cerisier</span>
        <span v-else class="sidebar-title-mini">C</span>
      </div>
      <div class="glow-line" />

      <el-scrollbar class="sidebar-scrollbar">
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapsed"
          :collapse-transition="false"
          router
          class="admin-menu"
          background-color="transparent"
          text-color="#94a3b8"
          active-text-color="#00d4ff"
        >
          <el-menu-item index="/admin/dashboard">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>Dashboard</template>
          </el-menu-item>

          <el-sub-menu index="blog">
            <template #title>
              <el-icon><Document /></el-icon>
              <span>Blog Management</span>
            </template>
            <el-menu-item index="/admin/posts">
              <el-icon><Document /></el-icon>
              <template #title>Posts</template>
            </el-menu-item>
            <el-menu-item index="/admin/categories">
              <el-icon><Folder /></el-icon>
              <template #title>Categories</template>
            </el-menu-item>
            <el-menu-item index="/admin/tags">
              <el-icon><PriceTag /></el-icon>
              <template #title>Tags</template>
            </el-menu-item>
            <el-menu-item index="/admin/comments">
              <el-icon><ChatDotRound /></el-icon>
              <template #title>Comments</template>
            </el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="quant">
            <template #title>
              <el-icon><TrendCharts /></el-icon>
              <span>Quant System</span>
            </template>
            <el-menu-item index="/admin/quant/dashboard">
              <el-icon><DataAnalysis /></el-icon>
              <template #title>Dashboard</template>
            </el-menu-item>
            <el-menu-item index="/admin/quant/picks">
              <el-icon><Star /></el-icon>
              <template #title>Stock Picks</template>
            </el-menu-item>
            <el-menu-item index="/admin/quant/simulator">
              <el-icon><Monitor /></el-icon>
              <template #title>Simulator</template>
            </el-menu-item>
            <el-menu-item index="/admin/quant/reports">
              <el-icon><Notebook /></el-icon>
              <template #title>Reports</template>
            </el-menu-item>
            <el-menu-item index="/admin/quant/settings">
              <el-icon><SetUp /></el-icon>
              <template #title>Settings</template>
            </el-menu-item>
          </el-sub-menu>

          <el-menu-item index="/admin/settings">
            <el-icon><Setting /></el-icon>
            <template #title>Site Settings</template>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <!-- Main area -->
    <el-container class="admin-main-container">
      <!-- Header -->
      <el-header class="admin-header" height="56px">
        <div class="header-left">
          <el-button
            class="collapse-btn"
            :icon="isCollapsed ? Expand : Fold"
            text
            @click="isCollapsed = !isCollapsed"
          />
        </div>
        <div class="header-right">
          <span class="header-username">{{ authStore.user?.username ?? 'Admin' }}</span>
          <el-button type="danger" text size="small" @click="handleLogout">
            <el-icon class="logout-icon"><SwitchButton /></el-icon>
            Logout
          </el-button>
        </div>
      </el-header>

      <!-- Content -->
      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DataAnalysis,
  Document,
  Folder,
  PriceTag,
  ChatDotRound,
  TrendCharts,
  Star,
  Monitor,
  Notebook,
  SetUp,
  Setting,
  Expand,
  Fold,
  SwitchButton,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isCollapsed = ref(false)

const activeMenu = computed(() => route.path)

onMounted(async () => {
  await authStore.init()
  if (!authStore.isAuthenticated) {
    router.replace({ name: 'admin-login' })
  }
})

function handleLogout() {
  authStore.logout()
  router.push({ name: 'admin-login' })
}
</script>

<style scoped>
.admin-layout {
  height: 100vh;
  background: var(--bg-primary);
}

/* Sidebar */
.admin-sidebar {
  background: var(--bg-surface);
  border-right: 1px solid var(--color-border);
  transition: width 0.25s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: 3px;
  text-shadow: 0 0 12px rgba(0, 212, 255, 0.4);
}

.sidebar-title-mini {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-primary);
  text-shadow: 0 0 12px rgba(0, 212, 255, 0.4);
}

.sidebar-scrollbar {
  flex: 1;
  overflow: hidden;
}

/* Menu styles */
.admin-menu {
  border-right: none;
  padding: 8px 0;
}

.admin-menu :deep(.el-menu-item) {
  height: 44px;
  line-height: 44px;
  margin: 2px 8px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.admin-menu :deep(.el-menu-item:hover) {
  background: rgba(0, 212, 255, 0.08) !important;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: rgba(0, 212, 255, 0.12) !important;
  color: var(--color-primary) !important;
}

.admin-menu :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  margin: 2px 8px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.admin-menu :deep(.el-sub-menu__title:hover) {
  background: rgba(0, 212, 255, 0.08) !important;
}

.admin-menu :deep(.el-sub-menu .el-menu-item) {
  padding-left: 52px !important;
  min-width: 0;
}

/* Header */
.admin-header {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.collapse-btn {
  color: var(--color-text-muted);
  font-size: 18px;
}

.collapse-btn:hover {
  color: var(--color-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-username {
  font-size: 14px;
  color: var(--color-text);
}

.logout-icon {
  margin-right: 4px;
}

/* Main content */
.admin-main-container {
  flex-direction: column;
}

.admin-main {
  background: var(--bg-primary);
  padding: 24px;
  overflow-y: auto;
}
</style>
