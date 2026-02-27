<template>
  <div class="settings-page">
    <h1 class="page-title">Quant Settings</h1>

    <!-- Section 1: Factor Weights -->
    <el-card class="dark-card section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">Factor Weights</span>
        </div>
      </template>

      <!-- Style Tabs -->
      <el-tabs v-model="selectedStyle" class="style-tabs" @tab-change="onStyleChange">
        <el-tab-pane label="Ultra-Short" name="ultra_short" />
        <el-tab-pane label="Swing" name="swing" />
        <el-tab-pane label="Mid-Long" name="mid_long" />
      </el-tabs>

      <!-- Loading -->
      <div v-if="weightsLoading" class="weights-loading">
        <el-skeleton animated :rows="6" />
      </div>

      <!-- Error -->
      <div v-else-if="weightsError" class="weights-error">
        <p>{{ weightsError }}</p>
        <el-button type="primary" size="small" @click="loadWeights">Retry</el-button>
      </div>

      <!-- Sliders -->
      <div v-else class="weights-sliders">
        <div
          v-for="(value, factor) in currentWeights"
          :key="factor"
          class="weight-row"
        >
          <span class="weight-label">{{ formatFactorName(factor as string) }}</span>
          <el-slider
            :model-value="Math.round(value * 100)"
            :min="0"
            :max="100"
            :step="1"
            :format-tooltip="(val: number) => (val / 100).toFixed(2)"
            class="weight-slider"
            @update:model-value="(val: number) => updateWeight(factor as string, val)"
          />
          <span class="weight-value">{{ (value as number).toFixed(2) }}</span>
        </div>

        <!-- Sum validation -->
        <div class="weight-sum" :class="{ 'weight-sum--warning': !isSumValid }">
          <span class="weight-sum-label">Sum:</span>
          <span class="weight-sum-value">{{ weightSum.toFixed(2) }}</span>
          <span v-if="!isSumValid" class="weight-sum-hint">
            (should be close to 1.00)
          </span>
          <el-tag v-else type="success" size="small" effect="dark">Valid</el-tag>
        </div>

        <!-- Actions -->
        <div class="weight-actions">
          <el-button type="primary" :loading="weightsSaving" @click="saveWeights">
            Save
          </el-button>
          <el-button :loading="weightsLoading" @click="loadWeights">
            Reset
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- Section 2: API Keys -->
    <el-card class="dark-card section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">API Keys</span>
        </div>
      </template>

      <div class="dark-form api-keys-form">
        <el-alert
          type="info"
          :closable="false"
          class="api-keys-info"
        >
          API keys are configured via environment variables on the server.
          Values shown here are masked and read-only.
        </el-alert>

        <div class="form-row">
          <label class="form-label">DeepSeek API Key</label>
          <el-input
            model-value="sk-****************************"
            type="password"
            show-password
            disabled
            placeholder="Configured via DEEPSEEK_API_KEY env var"
          />
        </div>

        <div class="form-row">
          <label class="form-label">OpenAI API Key</label>
          <el-input
            model-value="sk-****************************"
            type="password"
            show-password
            disabled
            placeholder="Configured via OPENAI_API_KEY env var"
          />
        </div>
      </div>
    </el-card>

    <!-- Section 3: Celery Task Status -->
    <el-card class="dark-card section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">Celery Task Monitor</span>
          <el-button size="small" @click="loadTasks">
            Refresh
          </el-button>
        </div>
      </template>

      <!-- Loading -->
      <div v-if="tasksLoading" class="tasks-loading">
        <el-skeleton animated :rows="4" />
      </div>

      <!-- Error -->
      <div v-else-if="tasksError" class="tasks-error">
        <p>{{ tasksError }}</p>
        <el-button type="primary" size="small" @click="loadTasks">Retry</el-button>
      </div>

      <!-- Task Table -->
      <div v-else>
        <div class="tasks-count">
          <span>Scheduled tasks: <strong>{{ scheduleCount }}</strong></span>
        </div>

        <el-table
          :data="taskRows"
          class="dark-table"
          stripe
          :header-cell-style="tableHeaderStyle"
          :cell-style="tableCellStyle"
        >
          <el-table-column prop="name" label="Task Name" min-width="200">
            <template #default="{ row }">
              <span class="task-name">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="taskPath" label="Task Path" min-width="280">
            <template #default="{ row }">
              <span class="task-path">{{ row.taskPath }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="schedule" label="Schedule" min-width="160">
            <template #default="{ row }">
              <el-tag size="small" effect="plain" class="schedule-tag">
                {{ row.schedule }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="kwargs" label="Kwargs" min-width="140">
            <template #default="{ row }">
              <span class="task-kwargs">{{ row.kwargs }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="120" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                :loading="triggeringTask === row.taskPath"
                @click="triggerTask(row.taskPath)"
              >
                Trigger
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { ElNotification } from 'element-plus'
import { quantApi, type FactorWeights } from '@/api/quant'

// ---- Factor Weights State ----
const selectedStyle = ref('ultra_short')
const allWeights = ref<FactorWeights>({})
const weightsLoading = ref(false)
const weightsSaving = ref(false)
const weightsError = ref<string | null>(null)

// Local editable copy of weights for the selected style
const editableWeights = reactive<Record<string, Record<string, number>>>({})

const currentWeights = computed(() => {
  return editableWeights[selectedStyle.value] ?? {}
})

const weightSum = computed(() => {
  const weights = currentWeights.value
  return Object.values(weights).reduce((sum, val) => sum + val, 0)
})

const isSumValid = computed(() => {
  return Math.abs(weightSum.value - 1.0) < 0.05
})

async function loadWeights() {
  weightsLoading.value = true
  weightsError.value = null
  try {
    const { data } = await quantApi.getFactorWeights()
    allWeights.value = data
    // Initialize editable copies for all styles
    for (const style of Object.keys(data)) {
      editableWeights[style] = { ...data[style] }
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to load factor weights'
    weightsError.value = message
  } finally {
    weightsLoading.value = false
  }
}

function onStyleChange() {
  // If style weights not loaded yet into editable, copy from original
  if (!editableWeights[selectedStyle.value] && allWeights.value[selectedStyle.value]) {
    editableWeights[selectedStyle.value] = { ...allWeights.value[selectedStyle.value] }
  }
}

function updateWeight(factor: string, val: number) {
  if (!editableWeights[selectedStyle.value]) return
  editableWeights[selectedStyle.value][factor] = val / 100
}

async function saveWeights() {
  weightsSaving.value = true
  try {
    await quantApi.updateFactorWeights({
      style: selectedStyle.value,
      weights: editableWeights[selectedStyle.value],
    })
    ElNotification({
      title: 'Weights Saved',
      message: 'Factor weights updated successfully.',
      type: 'success',
    })
  } catch {
    // The API returns 501 since persistence is not implemented yet
    ElNotification({
      title: 'Not Persisted',
      message: 'Weight persistence is not yet implemented on the server. Changes are local only.',
      type: 'info',
      duration: 5000,
    })
  } finally {
    weightsSaving.value = false
  }
}

function formatFactorName(factor: string): string {
  return factor
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// ---- Celery Tasks State ----
const tasksLoading = ref(false)
const tasksError = ref<string | null>(null)
const scheduleCount = ref(0)
const taskRows = ref<TaskRow[]>([])
const triggeringTask = ref<string | null>(null)

interface TaskRow {
  name: string
  taskPath: string
  schedule: string
  kwargs: string
}

async function loadTasks() {
  tasksLoading.value = true
  tasksError.value = null
  try {
    const { data } = await quantApi.getTasks()
    scheduleCount.value = data.schedule_count
    taskRows.value = Object.entries(data.beat_schedule).map(([name, info]) => ({
      name,
      taskPath: info.task,
      schedule: info.schedule,
      kwargs: info.kwargs ? JSON.stringify(info.kwargs) : '--',
    }))
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to load task schedule'
    tasksError.value = message
  } finally {
    tasksLoading.value = false
  }
}

async function triggerTask(taskPath: string) {
  triggeringTask.value = taskPath
  try {
    const { data } = await quantApi.triggerTask({ task: taskPath })
    ElNotification({
      title: 'Task Triggered',
      message: `Task "${data.task_name}" queued with ID: ${data.task_id}`,
      type: 'success',
      duration: 4000,
    })
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to trigger task'
    ElNotification({
      title: 'Trigger Failed',
      message,
      type: 'error',
    })
  } finally {
    triggeringTask.value = null
  }
}

// ---- Table Style Helpers ----
const tableHeaderStyle = () => ({
  background: '#0f1923',
  color: '#94a3b8',
  borderColor: '#1e3a5f',
  fontWeight: '600',
  fontSize: '12px',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.5px',
})

const tableCellStyle = () => ({
  background: 'transparent',
  color: '#e2e8f0',
  borderColor: '#1e3a5f',
})

// ---- Lifecycle ----
onMounted(() => {
  loadWeights()
  loadTasks()
})
</script>

<style scoped>
.settings-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 24px;
}

/* Section Card */
.section-card {
  margin-bottom: 24px;
}

/* Dark Card Overrides */
.dark-card {
  background: var(--bg-surface);
  border: 1px solid var(--color-border);
}

.dark-card :deep(.el-card__header) {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 16px 20px;
}

.dark-card :deep(.el-card__body) {
  background: var(--bg-surface);
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

/* Style Tabs */
.style-tabs {
  margin-bottom: 20px;
}

.style-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: var(--color-border);
}

.style-tabs :deep(.el-tabs__item) {
  color: var(--color-text-muted);
  font-size: 14px;
  font-weight: 500;
}

.style-tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary);
}

.style-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--color-primary);
}

.style-tabs :deep(.el-tabs__item:hover) {
  color: var(--color-primary);
}

/* Weights Loading / Error */
.weights-loading :deep(.el-skeleton__item) {
  background: var(--bg-surface-light);
}

.weights-error,
.tasks-error {
  color: #ef4444;
  text-align: center;
  padding: 20px;
}

.weights-error p,
.tasks-error p {
  margin-bottom: 12px;
}

/* Weight Sliders */
.weights-sliders {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.weight-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.weight-label {
  min-width: 160px;
  font-size: 14px;
  color: var(--color-text);
  flex-shrink: 0;
}

.weight-slider {
  flex: 1;
}

.weight-slider :deep(.el-slider__runway) {
  background: var(--bg-surface-light);
}

.weight-slider :deep(.el-slider__bar) {
  background: var(--color-primary);
}

.weight-slider :deep(.el-slider__button) {
  border-color: var(--color-primary);
  background: var(--bg-surface);
}

.weight-slider :deep(.el-slider__button:hover),
.weight-slider :deep(.el-slider__button.dragging) {
  border-color: var(--color-primary);
}

.weight-value {
  min-width: 48px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
  font-family: monospace;
}

/* Weight Sum */
.weight-sum {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--bg-surface-light);
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.weight-sum--warning {
  border-color: #f59e0b;
}

.weight-sum-label {
  font-size: 14px;
  color: var(--color-text-muted);
}

.weight-sum-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
  font-family: monospace;
}

.weight-sum--warning .weight-sum-value {
  color: #f59e0b;
}

.weight-sum-hint {
  font-size: 12px;
  color: #f59e0b;
}

/* Weight Actions */
.weight-actions {
  display: flex;
  gap: 12px;
  padding-top: 8px;
}

/* API Keys Section */
.api-keys-info {
  margin-bottom: 20px;
}

.api-keys-info :deep(.el-alert__content) {
  color: var(--color-text);
}

.dark-form .form-row {
  margin-bottom: 16px;
}

.dark-form .form-row:last-child {
  margin-bottom: 0;
}

.dark-form .form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 8px;
}

.dark-form :deep(.el-input__wrapper) {
  background: var(--bg-surface-light);
  box-shadow: 0 0 0 1px var(--color-border) inset;
  color: var(--color-text);
}

.dark-form :deep(.el-input__inner) {
  color: var(--color-text);
}

.dark-form :deep(.el-input.is-disabled .el-input__wrapper) {
  background: var(--bg-surface-light);
  box-shadow: 0 0 0 1px var(--color-border) inset;
  cursor: not-allowed;
}

.dark-form :deep(.el-input.is-disabled .el-input__inner) {
  color: var(--color-text-muted);
  -webkit-text-fill-color: var(--color-text-muted);
}

/* Celery Tasks Section */
.tasks-loading :deep(.el-skeleton__item) {
  background: var(--bg-surface-light);
}

.tasks-count {
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--color-text-muted);
}

.tasks-count strong {
  color: var(--color-primary);
}

/* Dark Table */
.dark-table {
  --el-table-bg-color: var(--bg-surface);
  --el-table-tr-bg-color: var(--bg-surface);
  --el-table-row-hover-bg-color: var(--bg-surface-light);
  --el-table-header-bg-color: #0f1923;
  --el-table-border-color: var(--color-border);
  --el-table-text-color: var(--color-text);
  --el-fill-color-lighter: var(--bg-surface-light);
}

.dark-table :deep(.el-table__inner-wrapper::before) {
  background-color: var(--color-border);
}

.dark-table :deep(th.el-table__cell) {
  background: #0f1923 !important;
}

.task-name {
  font-weight: 600;
  color: var(--color-text);
}

.task-path {
  font-family: monospace;
  font-size: 12px;
  color: var(--color-text-muted);
}

.schedule-tag {
  background: var(--bg-surface-light) !important;
  border-color: var(--color-border) !important;
  color: var(--color-text-muted) !important;
  font-family: monospace;
}

.task-kwargs {
  font-family: monospace;
  font-size: 12px;
  color: var(--color-text-muted);
}

/* Responsive */
@media (max-width: 768px) {
  .page-title {
    font-size: 20px;
    margin-bottom: 16px;
  }

  .weight-row {
    flex-wrap: wrap;
    gap: 8px;
  }

  .weight-label {
    min-width: 120px;
    font-size: 13px;
  }

  .weight-value {
    min-width: 40px;
  }
}
</style>
