<template>
  <div>
    <!-- Hero Section -->
    <HeroSection
      :totalPosts="totalPosts"
      :totalCategories="categories.length"
      :totalTags="tags.length"
    />

    <!-- Latest Posts -->
    <section>
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold" style="color: var(--color-text);">
          <span style="color: var(--color-primary);">#</span> 最新文章
        </h2>
        <router-link to="/posts" class="text-sm no-underline"
                     style="color: var(--color-text-muted);">
          查看全部 &rarr;
        </router-link>
      </div>

      <!-- Loading state -->
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
        <PostCard
          v-for="(post, index) in posts"
          :key="post.id"
          :post="post"
          class="animate-fade-in-up"
          :style="{ animationDelay: `${index * 0.1}s` }"
        />
      </div>

      <!-- Empty state -->
      <div v-else class="text-center py-20">
        <p class="text-lg" style="color: var(--color-text-muted);">暂无文章，敬请期待...</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { blogApi } from '@/api/blog'
import type { Post, Category, Tag } from '@/api/blog'
import PostCard from '@/components/blog/PostCard.vue'
import HeroSection from '@/components/blog/HeroSection.vue'

const posts = ref<Post[]>([])
const categories = ref<Category[]>([])
const tags = ref<Tag[]>([])
const totalPosts = ref(0)
const loading = ref(true)

onMounted(async () => {
  try {
    const [postsRes, catsRes, tagsRes] = await Promise.all([
      blogApi.getPosts({ page: 1 }),
      blogApi.getCategories(),
      blogApi.getTags(),
    ])
    posts.value = postsRes.data.results
    totalPosts.value = postsRes.data.count
    categories.value = catsRes.data
    tags.value = tagsRes.data
  } catch (err) {
    console.error('Failed to load homepage data:', err)
  } finally {
    loading.value = false
  }
})
</script>
