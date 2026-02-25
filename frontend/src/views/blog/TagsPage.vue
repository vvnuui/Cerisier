<template>
  <div>
    <h1 class="text-3xl font-bold mb-8" style="color: var(--color-text);">
      <span style="color: var(--color-primary);">#</span> 标签
    </h1>

    <!-- Loading skeleton -->
    <div v-if="loading" class="card p-8">
      <div class="flex flex-wrap justify-center gap-3">
        <div
          v-for="n in 12"
          :key="n"
          class="animate-pulse rounded-full"
          :style="{
            backgroundColor: 'var(--bg-surface-light)',
            width: `${60 + Math.random() * 40}px`,
            height: '28px',
          }"
        ></div>
      </div>
    </div>

    <!-- Tag cloud -->
    <div v-else-if="tags.length" class="card p-8 animate-fade-in-up">
      <div class="flex flex-wrap justify-center items-center gap-3">
        <router-link
          v-for="tag in tags"
          :key="tag.id"
          :to="`/posts?tag=${tag.slug}`"
          class="tag-item no-underline inline-block px-3 py-1.5 rounded-full transition-all"
          :style="tagStyle(tag)"
        >
          {{ tag.name }}
          <span class="tag-count">{{ tag.post_count }}</span>
        </router-link>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-20">
      <p style="color: var(--color-text-muted);">暂无标签</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { blogApi } from '@/api/blog'
import type { Tag } from '@/api/blog'

const tags = ref<Tag[]>([])
const loading = ref(true)

const maxCount = computed(() => Math.max(...tags.value.map((t) => t.post_count), 1))
const minCount = computed(() => Math.min(...tags.value.map((t) => t.post_count), 0))

function ratio(tag: Tag): number {
  const range = maxCount.value - minCount.value
  if (range === 0) return 1
  return (tag.post_count - minCount.value) / range
}

function tagStyle(tag: Tag) {
  const r = ratio(tag)
  const fontSize = 0.8 + r * 0.6 // 0.8rem - 1.4rem
  const opacity = 0.6 + r * 0.4 // 0.6 - 1.0
  const color = tag.color || '#00d4ff'

  return {
    fontSize: `${fontSize}rem`,
    opacity,
    color,
    backgroundColor: hexToRgba(color, 0.2),
  }
}

function hexToRgba(hex: string, alpha: number): string {
  const cleaned = hex.replace('#', '')
  const r = parseInt(cleaned.substring(0, 2), 16)
  const g = parseInt(cleaned.substring(2, 4), 16)
  const b = parseInt(cleaned.substring(4, 6), 16)
  if (isNaN(r) || isNaN(g) || isNaN(b)) {
    return `rgba(0, 212, 255, ${alpha})`
  }
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

onMounted(async () => {
  try {
    const res = await blogApi.getTags()
    tags.value = res.data
  } catch {
    tags.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.tag-item {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.tag-item:hover {
  transform: scale(1.1);
  box-shadow: 0 0 12px rgba(0, 212, 255, 0.2);
}

.tag-count {
  display: inline-block;
  margin-left: 4px;
  font-size: 0.7em;
  opacity: 0.7;
}
</style>
