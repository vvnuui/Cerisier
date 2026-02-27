<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-3xl font-bold" style="color: var(--color-text);">
        <span style="color: var(--color-primary);">#</span>
        {{ pageTitle }}
      </h1>
      <!-- Active filter chip -->
      <div v-if="activeFilter" class="flex items-center gap-2">
        <span class="text-sm px-3 py-1 rounded-full"
              style="background-color: rgba(0, 212, 255, 0.15); color: var(--color-primary);">
          {{ activeFilter }}
        </span>
        <button @click="clearFilter" class="text-xs" style="color: var(--color-text-muted);">
          &times; 清除
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="n in 6" :key="n" class="card animate-pulse">
        <div class="h-48" style="background-color: var(--bg-surface-light);"></div>
        <div class="p-4 space-y-3">
          <div class="h-4 rounded" style="background-color: var(--bg-surface-light); width: 60%;"></div>
          <div class="h-3 rounded" style="background-color: var(--bg-surface-light); width: 80%;"></div>
        </div>
      </div>
    </div>

    <!-- Posts grid -->
    <div v-else-if="posts.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <PostCard v-for="post in posts" :key="post.id" :post="post" />
    </div>

    <!-- Empty -->
    <div v-else class="text-center py-20">
      <p style="color: var(--color-text-muted);">暂无相关文章</p>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex justify-center mt-10 gap-2">
      <button
        v-for="p in totalPages" :key="p"
        @click="goToPage(p)"
        class="w-10 h-10 rounded-lg text-sm font-medium transition-all"
        :style="{
          backgroundColor: p === currentPage ? 'rgba(0, 212, 255, 0.2)' : 'var(--bg-surface)',
          color: p === currentPage ? 'var(--color-primary)' : 'var(--color-text-muted)',
          border: `1px solid ${p === currentPage ? 'var(--color-primary)' : 'var(--color-border)'}`,
        }"
      >
        {{ p }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { blogApi } from '@/api/blog'
import type { Post } from '@/api/blog'
import PostCard from '@/components/blog/PostCard.vue'

const route = useRoute()
const router = useRouter()

const posts = ref<Post[]>([])
const totalCount = ref(0)
const loading = ref(true)
const currentPage = ref(1)
const pageSize = 10

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize))

const activeFilter = computed(() => {
  if (route.query.category) return `分类: ${route.query.category}`
  if (route.query.tag) return `标签: ${route.query.tag}`
  return ''
})

const pageTitle = computed(() => {
  if (route.query.category) return '分类文章'
  if (route.query.tag) return '标签文章'
  return '全部文章'
})

async function fetchPosts() {
  loading.value = true
  try {
    const res = await blogApi.getPosts({
      page: currentPage.value,
      category: route.query.category as string | undefined,
      tag: route.query.tag as string | undefined,
    })
    posts.value = res.data.results
    totalCount.value = res.data.count
  } catch (err) {
    console.error('Failed to load posts:', err)
  } finally {
    loading.value = false
  }
}

function goToPage(page: number) {
  currentPage.value = page
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function clearFilter() {
  router.push('/posts')
}

onMounted(fetchPosts)
watch([currentPage, () => route.query], fetchPosts)
</script>
