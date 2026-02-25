<template>
  <div v-if="loading" class="animate-pulse space-y-4">
    <div class="h-8 rounded" style="background-color: var(--bg-surface-light); width: 60%;"></div>
    <div class="h-4 rounded" style="background-color: var(--bg-surface-light); width: 30%;"></div>
    <div class="h-64 rounded" style="background-color: var(--bg-surface-light);"></div>
  </div>

  <article v-else-if="post" class="max-w-4xl mx-auto">
    <!-- Header -->
    <header class="mb-8">
      <h1 class="text-3xl md:text-4xl font-bold mb-4" style="color: var(--color-text);">
        {{ post.title }}
      </h1>

      <!-- Meta -->
      <div class="flex items-center flex-wrap gap-4 mb-4 text-sm" style="color: var(--color-text-muted);">
        <span>{{ post.author_name }}</span>
        <span>&middot;</span>
        <span>{{ formatDate(post.published_at || post.created_at) }}</span>
        <span>&middot;</span>
        <span>{{ post.view_count }} 阅读</span>
        <span v-if="post.updated_at !== post.created_at">
          &middot; 更新于 {{ formatDate(post.updated_at) }}
        </span>
      </div>

      <!-- Tags -->
      <div class="flex items-center gap-2 flex-wrap">
        <router-link v-if="post.category" :to="`/posts?category=${post.category.slug}`"
                     class="text-xs px-3 py-1 rounded-full no-underline"
                     style="background-color: rgba(0, 212, 255, 0.15); color: var(--color-primary);">
          {{ post.category.name }}
        </router-link>
        <router-link v-for="tag in post.tags" :key="tag.id" :to="`/posts?tag=${tag.slug}`"
                     class="text-xs px-3 py-1 rounded-full no-underline"
                     :style="{ backgroundColor: tag.color + '20', color: tag.color }">
          {{ tag.name }}
        </router-link>
      </div>

      <div class="glow-line mt-6"></div>
    </header>

    <!-- Cover image -->
    <div v-if="post.cover_image" class="mb-8 rounded-xl overflow-hidden glow-border">
      <img :src="post.cover_image" :alt="post.title" class="w-full" />
    </div>

    <!-- Content -->
    <div class="prose-content" v-html="post.content"></div>

    <div class="glow-line my-10"></div>

    <!-- Comment Section -->
    <CommentSection :slug="post.slug" />
  </article>

  <!-- Not found -->
  <div v-else class="text-center py-20">
    <p class="text-xl" style="color: var(--color-text-muted);">文章未找到</p>
    <router-link to="/posts" class="mt-4 inline-block text-sm" style="color: var(--color-primary);">
      &larr; 返回文章列表
    </router-link>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { blogApi } from '@/api/blog'
import type { PostDetail } from '@/api/blog'
import CommentSection from '@/components/blog/CommentSection.vue'

const route = useRoute()
const post = ref<PostDetail | null>(null)
const loading = ref(true)

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric',
  })
}

onMounted(async () => {
  try {
    const res = await blogApi.getPost(route.params.slug as string)
    post.value = res.data
  } catch {
    post.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* Markdown content styling */
.prose-content {
  color: var(--color-text);
  line-height: 1.8;
  font-size: 1rem;
}

.prose-content :deep(h1),
.prose-content :deep(h2),
.prose-content :deep(h3),
.prose-content :deep(h4) {
  color: var(--color-text);
  margin-top: 2em;
  margin-bottom: 0.5em;
  font-weight: 700;
}

.prose-content :deep(h2) {
  font-size: 1.5rem;
  padding-bottom: 0.3em;
  border-bottom: 1px solid var(--color-border);
}

.prose-content :deep(h3) {
  font-size: 1.25rem;
}

.prose-content :deep(p) {
  margin-bottom: 1em;
}

.prose-content :deep(a) {
  color: var(--color-primary);
  text-decoration: underline;
}

.prose-content :deep(code) {
  background-color: var(--bg-surface);
  color: var(--color-accent);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.prose-content :deep(pre) {
  background-color: var(--bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1em;
  overflow-x: auto;
  margin: 1.5em 0;
}

.prose-content :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--color-text);
}

.prose-content :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: 1em;
  margin: 1.5em 0;
  color: var(--color-text-muted);
}

.prose-content :deep(ul), .prose-content :deep(ol) {
  padding-left: 1.5em;
  margin-bottom: 1em;
}

.prose-content :deep(li) {
  margin-bottom: 0.3em;
}

.prose-content :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 1.5em 0;
}

.prose-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5em 0;
}

.prose-content :deep(th),
.prose-content :deep(td) {
  border: 1px solid var(--color-border);
  padding: 0.5em 1em;
  text-align: left;
}

.prose-content :deep(th) {
  background-color: var(--bg-surface);
  font-weight: 600;
}

.prose-content :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
  margin: 2em 0;
}
</style>
