<template>
  <router-link :to="`/post/${post.slug}`" class="block card p-0 overflow-hidden group no-underline">
    <!-- Cover image -->
    <div class="relative h-48 overflow-hidden" style="background-color: var(--bg-surface-light);">
      <img v-if="post.cover_image" :src="post.cover_image" :alt="post.title"
           class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" />
      <div v-else class="w-full h-full flex items-center justify-center">
        <svg class="w-12 h-12" style="color: var(--color-border);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>
      <!-- Pinned badge -->
      <div v-if="post.is_pinned" class="absolute top-2 left-2 px-2 py-1 rounded text-xs font-bold"
           style="background-color: var(--color-accent); color: white;">
        置顶
      </div>
    </div>

    <!-- Content -->
    <div class="p-4">
      <!-- Category & Tags -->
      <div class="flex items-center gap-2 mb-2 flex-wrap">
        <span v-if="post.category" class="text-xs px-2 py-0.5 rounded"
              style="background-color: rgba(0, 212, 255, 0.15); color: var(--color-primary);">
          {{ post.category.name }}
        </span>
        <span v-for="tag in post.tags.slice(0, 3)" :key="tag.id"
              class="text-xs px-2 py-0.5 rounded"
              :style="{ backgroundColor: tag.color + '20', color: tag.color }">
          {{ tag.name }}
        </span>
      </div>

      <!-- Title -->
      <h3 class="text-lg font-semibold mb-2 line-clamp-2 group-hover:text-[var(--color-primary)] transition-colors"
          style="color: var(--color-text);">
        {{ post.title }}
      </h3>

      <!-- Excerpt -->
      <p class="text-sm mb-3 line-clamp-2" style="color: var(--color-text-muted);">
        {{ post.excerpt || '暂无摘要' }}
      </p>

      <!-- Meta -->
      <div class="flex items-center justify-between text-xs" style="color: var(--color-text-muted);">
        <span>{{ formatDate(post.published_at || post.created_at) }}</span>
        <div class="flex items-center gap-3">
          <span class="flex items-center gap-1">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            {{ post.view_count }}
          </span>
          <span class="flex items-center gap-1">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            {{ post.like_count }}
          </span>
        </div>
      </div>
    </div>
  </router-link>
</template>

<script setup lang="ts">
import type { Post } from '@/api/blog'

defineProps<{ post: Post }>()

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}
</script>
