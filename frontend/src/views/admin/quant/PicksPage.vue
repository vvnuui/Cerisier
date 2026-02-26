<template>
  <div class="picks-page">
    <h1 class="page-title">Stock Picks</h1>

    <!-- Tabs: Ultra-Short / Swing / Mid-Long -->
    <el-tabs v-model="activeTab" class="picks-tabs" @tab-change="onTabChange">
      <el-tab-pane label="Ultra-Short" name="ultra_short" />
      <el-tab-pane label="Swing" name="swing" />
      <el-tab-pane label="Mid-Long" name="mid_long" />
    </el-tabs>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="i in 8" :key="i">
          <el-skeleton animated :rows="6" class="card-skeleton" />
        </el-col>
      </el-row>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <el-result icon="error" title="Failed to load recommendations" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="fetchPicks">Retry</el-button>
        </template>
      </el-result>
    </div>

    <!-- Empty State -->
    <div v-else-if="recommendations.length === 0" class="empty-container">
      <el-empty description="No recommendations available for this style." />
    </div>

    <!-- Cards Grid -->
    <el-row v-else :gutter="20" class="picks-grid">
      <el-col
        :xs="24"
        :sm="12"
        :md="8"
        :lg="6"
        v-for="rec in recommendations"
        :key="rec.stock_code"
      >
        <StockPickCard :recommendation="rec" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { quantApi, type Recommendation } from '@/api/quant'
import StockPickCard from '@/components/quant/StockPickCard.vue'

const activeTab = ref('swing')
const loading = ref(false)
const error = ref<string | null>(null)
const recommendations = ref<Recommendation[]>([])

async function fetchPicks() {
  loading.value = true
  error.value = null
  try {
    const { data } = await quantApi.getRecommendations({
      style: activeTab.value,
      limit: 20,
    })
    recommendations.value = data.results
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    error.value = message
    recommendations.value = []
  } finally {
    loading.value = false
  }
}

function onTabChange() {
  fetchPicks()
}

onMounted(() => {
  fetchPicks()
})
</script>

<style scoped>
.picks-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 24px;
}

/* Tabs styling */
.picks-tabs {
  margin-bottom: 24px;
}

.picks-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: var(--color-border);
}

.picks-tabs :deep(.el-tabs__item) {
  color: var(--color-text-muted);
  font-size: 14px;
  font-weight: 500;
}

.picks-tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary);
}

.picks-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--color-primary);
}

.picks-tabs :deep(.el-tabs__item:hover) {
  color: var(--color-primary);
}

/* Loading skeleton */
.loading-container .el-col {
  margin-bottom: 20px;
}

.card-skeleton {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px;
}

.card-skeleton :deep(.el-skeleton__item) {
  background: var(--bg-surface-light);
}

/* Error state */
.error-container {
  display: flex;
  justify-content: center;
  padding-top: 60px;
}

.error-container :deep(.el-result__title p) {
  color: var(--color-text);
}

.error-container :deep(.el-result__subtitle p) {
  color: var(--color-text-muted);
}

/* Empty state */
.empty-container {
  display: flex;
  justify-content: center;
  padding-top: 60px;
}

.empty-container :deep(.el-empty__description p) {
  color: var(--color-text-muted);
}

/* Grid */
.picks-grid .el-col {
  margin-bottom: 20px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .page-title {
    font-size: 20px;
    margin-bottom: 16px;
  }

  .picks-tabs {
    margin-bottom: 16px;
  }
}
</style>
