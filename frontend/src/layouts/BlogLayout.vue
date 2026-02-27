<template>
  <div class="min-h-screen flex flex-col" style="background-color: var(--bg-primary);">
    <!-- Navbar -->
    <nav class="sticky top-0 z-50 backdrop-blur-md border-b"
         style="background-color: rgba(10, 22, 40, 0.85); border-color: var(--color-border);">
      <div class="max-w-6xl mx-auto px-4 sm:px-6">
        <div class="flex items-center justify-between h-16">
          <!-- Logo -->
          <router-link to="/" class="flex items-center gap-2 no-underline">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center"
                 style="background: linear-gradient(135deg, var(--color-primary), var(--color-accent));">
              <span class="text-white font-bold text-sm">C</span>
            </div>
            <span class="text-xl font-bold glow-text" style="color: var(--color-primary);">
              Cerisier
            </span>
          </router-link>

          <!-- Desktop Nav Links -->
          <div class="hidden md:flex items-center gap-1">
            <router-link
              v-for="link in navLinks"
              :key="link.path"
              :to="link.path"
              class="nav-link px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300"
              :class="{ 'active': isActive(link.path) }"
            >
              {{ link.name }}
            </router-link>
          </div>

          <!-- Mobile menu button -->
          <button @click="mobileMenuOpen = !mobileMenuOpen"
                  class="md:hidden p-2 rounded-lg"
                  style="color: var(--color-text-muted);">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="!mobileMenuOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M4 6h16M4 12h16M4 18h16" />
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Mobile menu -->
        <div v-if="mobileMenuOpen" class="md:hidden pb-4">
          <router-link
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            class="block px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 nav-link"
            @click="mobileMenuOpen = false"
          >
            {{ link.name }}
          </router-link>
        </div>
      </div>

      <!-- Glow line at bottom of navbar -->
      <div class="glow-line"></div>
    </nav>

    <!-- Main content -->
    <main class="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-8 w-full">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Footer -->
    <footer class="border-t mt-auto" style="border-color: var(--color-border);">
      <div class="glow-line"></div>
      <div class="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div class="flex flex-col md:flex-row items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <span class="text-sm" style="color: var(--color-text-muted);">
              &copy; {{ currentYear }} Cerisier. Powered by Vue 3 &amp; Django.
            </span>
          </div>
          <div class="flex items-center gap-4">
            <a href="https://github.com" target="_blank" rel="noopener"
               class="text-sm hover:text-[var(--color-primary)]"
               style="color: var(--color-text-muted);">
              GitHub
            </a>
            <span style="color: var(--color-border);">|</span>
            <router-link to="/about" class="text-sm hover:text-[var(--color-primary)]"
                         style="color: var(--color-text-muted);">
              About
            </router-link>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const mobileMenuOpen = ref(false)
const currentYear = new Date().getFullYear()

const navLinks = [
  { name: '首页', path: '/' },
  { name: '文章', path: '/posts' },
  { name: '分类', path: '/categories' },
  { name: '标签', path: '/tags' },
  { name: '归档', path: '/archives' },
  { name: '关于', path: '/about' },
]

function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<style scoped>
.nav-link {
  color: var(--color-text-muted);
  text-decoration: none;
}
.nav-link:hover, .nav-link.active {
  color: var(--color-primary);
  background-color: rgba(0, 212, 255, 0.1);
}
.nav-link.active {
  text-shadow: 0 0 8px rgba(0, 212, 255, 0.4);
}

/* Page transition */
.page-enter-active, .page-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
