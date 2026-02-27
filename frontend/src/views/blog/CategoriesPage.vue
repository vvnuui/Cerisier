<template>
  <div>
    <h1 class="text-3xl font-bold mb-8" style="color: var(--color-text);">
      <span style="color: var(--color-primary);">#</span> 分类
    </h1>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div v-for="n in 4" :key="n" class="card p-4 animate-pulse">
        <div class="h-5 rounded" style="background-color: var(--bg-surface-light); width: 30%;"></div>
        <div class="h-3 rounded mt-2" style="background-color: var(--bg-surface-light); width: 60%;"></div>
      </div>
    </div>

    <!-- Category list -->
    <div v-else-if="categories.length" class="space-y-4">
      <div v-for="cat in categories" :key="cat.id" class="category-card card p-5 animate-fade-in-up">
        <router-link :to="`/posts?category=${cat.slug}`" class="no-underline block group">
          <div class="flex items-center justify-between mb-1">
            <h2 class="text-lg font-semibold group-hover:text-[var(--color-primary)] transition-colors"
                style="color: var(--color-text);">
              {{ cat.name }}
            </h2>
            <span class="text-sm px-2 py-0.5 rounded"
                  style="background-color: rgba(0, 212, 255, 0.15); color: var(--color-primary);">
              {{ cat.post_count }} 篇
            </span>
          </div>
          <p v-if="cat.description" class="text-sm" style="color: var(--color-text-muted);">
            {{ cat.description }}
          </p>
        </router-link>

        <!-- Children -->
        <div v-if="cat.children && cat.children.length" class="mt-3 pl-4 space-y-2"
             style="border-left: 2px solid var(--color-border);">
          <router-link v-for="child in cat.children" :key="child.id"
                       :to="`/posts?category=${child.slug}`"
                       class="flex items-center justify-between p-2 rounded-lg no-underline transition-all hover:bg-[rgba(0,212,255,0.05)]">
            <span class="text-sm" style="color: var(--color-text-muted);">{{ child.name }}</span>
            <span class="text-xs" style="color: var(--color-text-muted);">{{ child.post_count || 0 }} 篇</span>
          </router-link>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-20">
      <p style="color: var(--color-text-muted);">暂无分类</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { blogApi } from '@/api/blog'
import type { Category } from '@/api/blog'

const categories = ref<Category[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await blogApi.getCategories()
    categories.value = res.data
  } catch {
    categories.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.category-card {
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
}

.category-card:hover {
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.15), 0 0 30px rgba(0, 212, 255, 0.05);
  border-color: var(--color-primary);
}
</style>
