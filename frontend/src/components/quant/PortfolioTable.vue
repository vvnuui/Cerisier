<template>
  <div class="portfolio-table-wrapper">
    <div v-if="positions.length === 0" class="empty-state">
      <el-empty description="No positions in this portfolio yet." />
    </div>
    <div v-else class="table-container">
      <el-table
        :data="positions"
        class="dark-table"
        stripe
      >
        <el-table-column label="Code" prop="stock_code" width="110">
          <template #default="{ row }">
            <span class="cell-code">{{ row.stock_code }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Name" prop="stock_name" min-width="120">
          <template #default="{ row }">
            <span class="cell-text">{{ row.stock_name }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Shares" prop="shares" width="100" align="right">
          <template #default="{ row }">
            <span class="cell-text">{{ row.shares.toLocaleString() }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Avg Cost" prop="avg_cost" width="110" align="right">
          <template #default="{ row }">
            <span class="cell-text">{{ row.avg_cost.toFixed(2) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Current" prop="current_price" width="110" align="right">
          <template #default="{ row }">
            <span class="cell-text">{{ row.current_price.toFixed(2) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Market Value" prop="market_value" width="130" align="right">
          <template #default="{ row }">
            <span class="cell-text">{{ formatCurrency(row.market_value) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="P&L" prop="unrealized_pnl" width="120" align="right">
          <template #default="{ row }">
            <span :class="pnlClass(row.unrealized_pnl)">
              {{ row.unrealized_pnl >= 0 ? '+' : '' }}{{ formatCurrency(row.unrealized_pnl) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="P&L %" prop="unrealized_pnl_pct" width="100" align="right">
          <template #default="{ row }">
            <span :class="pnlClass(row.unrealized_pnl_pct)">
              {{ row.unrealized_pnl_pct >= 0 ? '+' : '' }}{{ row.unrealized_pnl_pct.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Position } from '@/api/quant'

defineProps<{
  positions: Position[]
}>()

function pnlClass(value: number): string {
  if (value > 0) return 'cell-profit'
  if (value < 0) return 'cell-loss'
  return 'cell-text'
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1e8) return (value / 1e8).toFixed(2) + '亿'
  if (Math.abs(value) >= 1e4) return (value / 1e4).toFixed(2) + '万'
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<style scoped>
.portfolio-table-wrapper {
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

.cell-profit {
  color: #10b981;
  font-weight: 600;
  font-size: 13px;
}

.cell-loss {
  color: #ef4444;
  font-weight: 600;
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
