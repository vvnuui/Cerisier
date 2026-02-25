<template>
  <div class="card p-4">
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm font-medium" style="color: var(--color-primary);">{{ comment.author_name }}</span>
      <span class="text-xs" style="color: var(--color-text-muted);">{{ formatDate(comment.created_at) }}</span>
    </div>
    <p class="text-sm mb-2" style="color: var(--color-text);">{{ comment.content }}</p>
    <button @click="$emit('reply', comment)" class="text-xs" style="color: var(--color-text-muted);">
      回复
    </button>

    <!-- Nested replies -->
    <div v-if="comment.replies && comment.replies.length" class="mt-3 pl-4 space-y-3"
         style="border-left: 2px solid var(--color-border);">
      <CommentItem v-for="reply in comment.replies" :key="reply.id" :comment="reply" @reply="$emit('reply', reply)" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  comment: {
    id: number
    author_name: string
    content: string
    created_at: string
    replies: any[]
  }
}>()

defineEmits<{
  reply: [comment: any]
}>()

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>
