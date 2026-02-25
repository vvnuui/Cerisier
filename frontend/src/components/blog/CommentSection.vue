<template>
  <section>
    <h3 class="text-xl font-bold mb-6" style="color: var(--color-text);">
      <span style="color: var(--color-primary);">#</span> 评论
    </h3>

    <!-- Comment form -->
    <div class="card p-4 mb-8">
      <div v-if="!isLoggedIn" class="grid grid-cols-2 gap-4 mb-4">
        <input v-model="form.nickname" placeholder="昵称 *" class="form-input" />
        <input v-model="form.email" type="email" placeholder="邮箱 *" class="form-input" />
      </div>
      <textarea v-model="form.content" rows="3" placeholder="留下你的评论..."
                class="form-input w-full mb-3 resize-none"></textarea>
      <div class="flex items-center justify-between">
        <span v-if="replyTo" class="text-xs" style="color: var(--color-text-muted);">
          回复 {{ replyTo.author_name }}
          <button @click="replyTo = null" class="ml-1" style="color: var(--color-accent);">&times;</button>
        </span>
        <span v-else></span>
        <button @click="submitComment" :disabled="submitting"
                class="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                style="background-color: var(--color-primary); color: var(--bg-primary);">
          {{ submitting ? '提交中...' : '发表评论' }}
        </button>
      </div>
      <p v-if="submitMsg" class="mt-2 text-xs" :style="{ color: submitError ? 'var(--color-accent)' : '#22c55e' }">
        {{ submitMsg }}
      </p>
    </div>

    <!-- Comments list -->
    <div v-if="comments.length" class="space-y-4">
      <CommentItem
        v-for="comment in comments" :key="comment.id"
        :comment="comment"
        @reply="handleReply"
      />
    </div>
    <p v-else class="text-sm" style="color: var(--color-text-muted);">暂无评论，快来第一个留言吧！</p>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { blogApi } from '@/api/blog'
import CommentItem from './CommentItem.vue'

const props = defineProps<{ slug: string }>()

interface CommentData {
  id: number
  author_name: string
  content: string
  created_at: string
  replies: CommentData[]
}

const comments = ref<CommentData[]>([])
const replyTo = ref<CommentData | null>(null)
const submitting = ref(false)
const submitMsg = ref('')
const submitError = ref(false)
const isLoggedIn = ref(!!localStorage.getItem('access_token'))

const form = ref({
  nickname: '',
  email: '',
  content: '',
})

async function loadComments() {
  try {
    const res = await blogApi.getComments(props.slug)
    comments.value = res.data
  } catch {
    comments.value = []
  }
}

async function submitComment() {
  if (!form.value.content.trim()) return
  submitting.value = true
  submitMsg.value = ''
  try {
    await blogApi.createComment(props.slug, {
      content: form.value.content,
      nickname: form.value.nickname || undefined,
      email: form.value.email || undefined,
      parent: replyTo.value?.id,
    })
    form.value.content = ''
    replyTo.value = null
    submitMsg.value = '评论提交成功，审核通过后将显示。'
    submitError.value = false
    await loadComments()
  } catch {
    submitMsg.value = '提交失败，请检查必填字段。'
    submitError.value = true
  } finally {
    submitting.value = false
  }
}

function handleReply(comment: CommentData) {
  replyTo.value = comment
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(loadComments)
</script>

<style scoped>
.form-input {
  background-color: var(--bg-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  outline: none;
  transition: border-color 0.3s;
}
.form-input:focus {
  border-color: var(--color-primary);
}
.form-input::placeholder {
  color: var(--color-text-muted);
}
</style>
