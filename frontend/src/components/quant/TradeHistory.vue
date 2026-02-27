<template>
  <div class="trade-history-wrapper">
    <div v-if="trades.length === 0" class="empty-state">
      <el-empty description="No trades executed yet." />
    </div>
    <div v-else class="table-container">
      <el-table
        :data="sortedTrades"
        class="dark-table"
        stripe
      >
        <el-table-column label="Date" width="160">
          <template #default="{ row }">
            <span class="cell-text-muted">{{ formatDate(row.executed_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Code" prop="stock_code" width="110">
          <template #default="{ row }">
            <span class="cell-code">{{ row.stock_code }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Type" width="90" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.trade_type === 'BUY' ? 'success' : 'danger'"
              size="small"
              effect="dark"
            >
              {{ row.trade_type }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Shares" prop="shares" width="100" align="right">
          <template #default="{ row }">
            <span class="cell-text">{{ row.shares.toLocaleString() }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Price" prop="price" width="100" align="right">
          <template #default="{ row }">
            <span class="cell-text">{{ row.price.toFixed(2) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Amount" prop="amount" width="130" align="right">
          <template #default="{ row }">
            <span class="cell-text">{{ formatCurrency(row.amount) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Commission" prop="commission" width="110" align="right">
          <template #default="{ row }">
            <span class="cell-text-muted">{{ row.commission.toFixed(2) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Reason" prop="reason" min-width="160">
          <template #default="{ row }">
            <span class="cell-text-muted" :title="row.reason">{{ truncate(row.reason, 40) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Trade } from '@/api/quant'

const props = defineProps<{
  trades: Trade[]
}>()

// Sort trades by date descending
const sortedTrades = computed(() => {
  return [...props.trades].sort(
    (a, b) => new Date(b.executed_at).getTime() - new Date(a.executed_at).getTime(),
  )
})

function formatDate(dateString: string): string {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1e8) return (value / 1e8).toFixed(2) + '亿'
  if (Math.abs(value) >= 1e4) return (value / 1e4).toFixed(2) + '万'
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function truncate(text: string, maxLength: number): string {
  if (!text) return '-'
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}
</script>

<style scoped>
.trade-history-wrapper {
  width: 100%;
}

.table-container {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

/* Dark table overrides */
.dark-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--bg-surface-light);
  --el-table-row-hover-bg-color: rgba(0, 212, 255, 0.06);
  --el-table-border-color: var(--color-border);
  --el-table-text-color: var(--color-text);
  --el-table-header-text-color: var(--color-text-muted);
  --el-fill-color-lighter: var(--bg-surface-light);
}

.dark-table :deep(.el-table__inner-wrapper::before) {
  background-color: var(--color-border);
}

.dark-table :deep(th.el-table__cell) {
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dark-table :deep(.el-table__body-wrapper .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: rgba(22, 33, 51, 0.5);
}

/* Cell styles */
.cell-code {
  color: var(--color-primary);
  font-family: monospace;
  font-size: 13px;
}

.cell-text {
  color: var(--color-text);
  font-size: 13px;
}

.cell-text-muted {
  color: var(--color-text-muted);
  font-size: 13px;
}

/* Empty state */
.empty-state {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.empty-state :deep(.el-empty__description p) {
  color: var(--color-text-muted);
}
</style>
