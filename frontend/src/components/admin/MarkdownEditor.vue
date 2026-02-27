<template>
  <div ref="editorRef" class="markdown-editor" />
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import Vditor from 'vditor'
import 'vditor/dist/index.css'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api/admin'

const props = withDefaults(defineProps<{
  modelValue: string
  height?: string
}>(), {
  height: '500px',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editorRef = ref<HTMLDivElement>()
let vditor: Vditor | null = null
let vditorReady = false

onMounted(() => {
  if (!editorRef.value) return

  vditor = new Vditor(editorRef.value, {
    height: props.height,
    mode: 'ir',
    theme: 'dark',
    icon: 'material',
    cache: {
      enable: false,
    },
    value: props.modelValue,
    preview: {
      theme: {
        current: 'dark',
      },
      hljs: {
        style: 'native',
      },
    },
    toolbar: [
      'bold',
      'italic',
      'strike',
      'headings',
      'list',
      'ordered-list',
      'check',
      'code',
      'inline-code',
      'quote',
      'table',
      'link',
      'upload',
      'line',
      'undo',
      'redo',
      'fullscreen',
    ],
    upload: {
      handler(files: File[]): null {
        for (const file of files) {
          adminApi.uploadImage(file).then((response) => {
            const url = response.data.url
            const filename = file.name
            if (vditor) {
              vditor.insertValue(`![${filename}](${url})`)
            }
          }).catch(() => {
            ElMessage.error('Image upload failed')
          })
        }
        return null
      },
      accept: 'image/*',
    },
    after: () => {
      vditorReady = true
      if (props.modelValue && vditor) {
        vditor.setValue(props.modelValue)
      }
    },
    input: (value: string) => {
      emit('update:modelValue', value)
    },
  })
})

onBeforeUnmount(() => {
  if (vditor) {
    vditor.destroy()
    vditor = null
  }
})

watch(() => props.modelValue, (newVal) => {
  if (vditor && vditorReady && newVal !== vditor.getValue()) {
    vditor.setValue(newVal)
  }
})
</script>

<style scoped>
.markdown-editor {
  width: 100%;
}

/* Dark theme overrides for Vditor */
.markdown-editor :deep(.vditor) {
  --panel-background-color: var(--bg-surface);
  border: 1px solid var(--color-border) !important;
  border-radius: 6px;
  overflow: hidden;
}

.markdown-editor :deep(.vditor-toolbar) {
  background: var(--bg-surface-light) !important;
  border-bottom: 1px solid var(--color-border) !important;
  padding: 4px 8px !important;
}

.markdown-editor :deep(.vditor-toolbar__item button) {
  color: var(--color-text-muted) !important;
}

.markdown-editor :deep(.vditor-toolbar__item button:hover) {
  color: var(--color-primary) !important;
  background: rgba(0, 212, 255, 0.08) !important;
}

.markdown-editor :deep(.vditor-ir) {
  background: var(--bg-surface) !important;
  color: var(--color-text) !important;
}

.markdown-editor :deep(.vditor-ir pre.vditor-reset) {
  color: var(--color-text) !important;
  background: var(--bg-surface) !important;
}

.markdown-editor :deep(.vditor-content .vditor-reset) {
  color: var(--color-text) !important;
}

.markdown-editor :deep(.vditor-counter) {
  color: var(--color-text-muted) !important;
  border-top: 1px solid var(--color-border) !important;
}
</style>
