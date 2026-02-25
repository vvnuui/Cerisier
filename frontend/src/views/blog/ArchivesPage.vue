<template>
  <div>
    <h1 class="text-3xl font-bold mb-8" style="color: var(--color-text);">
      <span style="color: var(--color-primary);">#</span> 归档
    </h1>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-8">
      <div v-for="n in 3" :key="n" class="flex gap-6">
        <div class="flex flex-col items-center">
          <div class="w-3 h-3 rounded-full animate-pulse" style="background-color: var(--bg-surface-light);"></div>
          <div class="w-0.5 flex-1 animate-pulse" style="background-color: var(--bg-surface-light);"></div>
        </div>
        <div class="flex-1 space-y-3 pb-8">
          <div class="h-5 rounded animate-pulse" style="background-color: var(--bg-surface-light); width: 120px;"></div>
          <div class="h-4 rounded animate-pulse" style="background-color: var(--bg-surface-light); width: 60%;"></div>
          <div class="h-4 rounded animate-pulse" style="background-color: var(--bg-surface-light); width: 45%;"></div>
        </div>
      </div>
    </div>

    <!-- Timeline -->
    <div v-else-if="sortedMonths.length" class="timeline animate-fade-in-up">
      <div v-for="month in sortedMonths" :key="month" class="timeline-group">
        <!-- Dot + line -->
        <div class="timeline-track">
          <div class="timeline-dot"></div>
          <div class="timeline-line"></div>
        </div>

        <!-- Content -->
        <div class="timeline-content">
          <h2 class="timeline-month glow-text">{{ formatMonth(month) }}</h2>
          <ul class="timeline-posts">
            <li v-for="post in archives[month]" :key="post.slug" class="timeline-post">
              <span class="post-day">{{ formatDay(post.published_at) }}</span>
              <router-link
                :to="`/post/${post.slug}`"
                class="post-title no-underline"
              >
                {{ post.title }}
              </router-link>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-20">
      <p style="color: var(--color-text-muted);">暂无归档</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { blogApi } from '@/api/blog'

type ArchivePost = { title: string; slug: string; published_at: string }
type Archives = Record<string, ArchivePost[]>

const archives = ref<Archives>({})
const loading = ref(true)

const sortedMonths = computed(() =>
  Object.keys(archives.value).sort((a, b) => b.localeCompare(a))
)

function formatMonth(key: string): string {
  // key is "YYYY-MM"
  const parts = key.split('-')
  const year = parts[0]
  const month = parts[1]
  return `${year} \u5e74 ${parseInt(month ?? '0', 10)} \u6708`
}

function formatDay(dateStr: string): string {
  const date = new Date(dateStr)
  return `${date.getDate()} \u65e5`
}

onMounted(async () => {
  try {
    const res = await blogApi.getArchives()
    archives.value = res.data
  } catch {
    archives.value = {}
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.timeline {
  position: relative;
}

.timeline-group {
  display: flex;
  gap: 1.5rem;
}

.timeline-track {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  width: 20px;
}

.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: var(--color-primary);
  box-shadow: 0 0 8px var(--color-primary), 0 0 16px rgba(0, 212, 255, 0.3);
  flex-shrink: 0;
  margin-top: 6px;
}

.timeline-line {
  width: 2px;
  flex: 1;
  background: linear-gradient(
    to bottom,
    var(--color-primary),
    rgba(0, 212, 255, 0.1)
  );
  min-height: 20px;
}

.timeline-group:last-child .timeline-line {
  background: linear-gradient(
    to bottom,
    var(--color-primary),
    transparent
  );
}

.timeline-content {
  flex: 1;
  padding-bottom: 2rem;
}

.timeline-month {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 0.75rem;
}

.timeline-posts {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.timeline-post {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  padding: 0.4rem 0.75rem;
  border-radius: 0.5rem;
  transition: background-color 0.2s ease;
}

.timeline-post:hover {
  background-color: rgba(0, 212, 255, 0.05);
}

.post-day {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  white-space: nowrap;
  min-width: 36px;
}

.post-title {
  color: var(--color-text);
  font-size: 0.95rem;
  transition: color 0.2s ease;
}

.post-title:hover {
  color: var(--color-primary);
}
</style>
