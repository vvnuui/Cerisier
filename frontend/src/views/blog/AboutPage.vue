<template>
  <div class="max-w-3xl mx-auto">
    <!-- Profile Header -->
    <div class="card p-8 mb-8 text-center animate-fade-in-up">
      <!-- Avatar -->
      <div class="w-24 h-24 mx-auto mb-4 rounded-full flex items-center justify-center"
           style="background: linear-gradient(135deg, var(--color-primary), var(--color-accent));">
        <span class="text-3xl font-bold text-white">C</span>
      </div>
      <h1 class="text-3xl font-bold mb-2 glow-text" style="color: var(--color-primary);">
        Cerisier
      </h1>
      <p class="text-sm mb-4" style="color: var(--color-text-muted);">
        Developer · Quant Enthusiast · Lifelong Learner
      </p>
      <div class="glow-line mx-auto w-24"></div>
      <p class="mt-4 leading-relaxed" style="color: var(--color-text);">
        热爱技术，专注于全栈开发与量化投资。相信数据驱动决策的力量，
        用代码连接创意与现实。这里记录着我的技术探索与投资思考。
      </p>
    </div>

    <!-- Tech Stack -->
    <div class="card p-6 mb-8 animate-fade-in-up" style="animation-delay: 0.1s;">
      <h2 class="text-xl font-bold mb-4" style="color: var(--color-text);">
        <span style="color: var(--color-primary);">&lt;/&gt;</span> 技术栈
      </h2>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div v-for="tech in techStack" :key="tech.name"
             class="p-3 rounded-lg text-center transition-all hover:scale-105"
             :style="{ backgroundColor: tech.color + '15', border: `1px solid ${tech.color}30` }">
          <div class="text-sm font-medium" :style="{ color: tech.color }">{{ tech.name }}</div>
          <div class="text-xs mt-0.5" style="color: var(--color-text-muted);">{{ tech.desc }}</div>
        </div>
      </div>
    </div>

    <!-- Interests -->
    <div class="card p-6 mb-8 animate-fade-in-up" style="animation-delay: 0.2s;">
      <h2 class="text-xl font-bold mb-4" style="color: var(--color-text);">
        <span style="color: var(--color-accent);">&#9733;</span> 兴趣领域
      </h2>
      <div class="flex flex-wrap gap-2">
        <span v-for="interest in interests" :key="interest"
              class="px-3 py-1.5 rounded-full text-sm"
              style="background-color: rgba(0, 212, 255, 0.1); color: var(--color-primary); border: 1px solid rgba(0, 212, 255, 0.2);">
          {{ interest }}
        </span>
      </div>
    </div>

    <!-- Contact -->
    <div class="card p-6 animate-fade-in-up" style="animation-delay: 0.3s;">
      <h2 class="text-xl font-bold mb-4" style="color: var(--color-text);">
        <span style="color: var(--color-primary);">@</span> 联系方式
      </h2>
      <div class="space-y-3">
        <a href="https://github.com" target="_blank" rel="noopener"
           class="flex items-center gap-3 p-3 rounded-lg no-underline transition-all"
           style="color: var(--color-text);"
           onmouseover="this.style.backgroundColor='rgba(0,212,255,0.05)'"
           onmouseout="this.style.backgroundColor='transparent'">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center"
               style="background-color: var(--bg-surface-light);">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
          </div>
          <span class="text-sm">GitHub</span>
        </a>
        <a href="mailto:hello@example.com"
           class="flex items-center gap-3 p-3 rounded-lg no-underline transition-all"
           style="color: var(--color-text);"
           onmouseover="this.style.backgroundColor='rgba(0,212,255,0.05)'"
           onmouseout="this.style.backgroundColor='transparent'">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center"
               style="background-color: var(--bg-surface-light);">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <span class="text-sm">hello@example.com</span>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const techStack = [
  { name: 'Vue 3', desc: '前端框架', color: '#42b883' },
  { name: 'TypeScript', desc: '类型安全', color: '#3178c6' },
  { name: 'Tailwind', desc: 'CSS 框架', color: '#06b6d4' },
  { name: 'Django', desc: '后端框架', color: '#092e20' },
  { name: 'PostgreSQL', desc: '数据库', color: '#336791' },
  { name: 'Redis', desc: '缓存/队列', color: '#dc382d' },
  { name: 'Docker', desc: '容器化', color: '#2496ed' },
  { name: 'ECharts', desc: '数据可视化', color: '#e43961' },
  { name: 'Celery', desc: '异步任务', color: '#a9cc54' },
]

const interests = [
  '全栈开发', '量化投资', 'A股分析', '数据可视化',
  '机器学习', '开源项目', '技术写作', 'DevOps',
]
</script>
