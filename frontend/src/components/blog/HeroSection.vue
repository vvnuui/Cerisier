<template>
  <section class="relative py-20 mb-12 text-center overflow-hidden rounded-2xl"
           style="background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(0, 212, 255, 0.05) 100%); border: 1px solid var(--color-border);">
    <!-- Decorative grid background -->
    <div class="absolute inset-0 opacity-10"
         style="background-image: radial-gradient(circle at 1px 1px, var(--color-primary) 1px, transparent 0); background-size: 40px 40px;">
    </div>

    <!-- Content -->
    <div class="relative z-10">
      <h1 class="text-5xl md:text-6xl font-bold mb-4 glow-text" style="color: var(--color-primary);">
        Cerisier
      </h1>
      <p class="text-lg md:text-xl mb-2" style="color: var(--color-text);">
        Code · Data · Insights
      </p>
      <p class="text-sm" style="color: var(--color-text-muted);">
        记录技术探索与量化投资的旅程
      </p>

      <!-- Decorative line -->
      <div class="mx-auto mt-6 w-32 glow-line"></div>

      <!-- Stats -->
      <div class="flex justify-center gap-8 mt-8">
        <div class="text-center">
          <div class="text-2xl font-bold" style="color: var(--color-primary);">{{ totalPosts }}</div>
          <div class="text-xs" style="color: var(--color-text-muted);">文章</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold" style="color: var(--color-accent);">{{ totalCategories }}</div>
          <div class="text-xs" style="color: var(--color-text-muted);">分类</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold" style="color: #42b883;">{{ totalTags }}</div>
          <div class="text-xs" style="color: var(--color-text-muted);">标签</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  totalPosts: number
  totalCategories: number
  totalTags: number
}>()
</script>
