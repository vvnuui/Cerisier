import apiClient from './client'

export interface AdminPost {
  id: number
  title: string
  slug: string
  content: string
  content_markdown: string
  excerpt: string
  cover_image: string | null
  category_id: number | null
  tag_ids: number[]
  status: 'draft' | 'published' | 'archived'
  is_pinned: boolean
  view_count: number
  like_count: number
  created_at: string
  updated_at: string
  published_at: string | null
}

export interface DashboardStats {
  total_posts: number
  total_views: number
  total_comments: number
  pending_comments: number
  posts_by_month: Array<{ month: string; count: number }>
  recent_comments: Array<{
    id: number
    post_title: string
    author_name: string
    content: string
    is_approved: boolean
    created_at: string
  }>
}

export const adminApi = {
  // Dashboard
  getDashboard() {
    return apiClient.get<DashboardStats>('/admin/dashboard/')
  },

  // Posts
  getPosts(params?: { page?: number; status?: string; search?: string }) {
    return apiClient.get('/admin/posts/', { params })
  },
  getPost(id: number) {
    return apiClient.get<AdminPost>(`/admin/posts/${id}/`)
  },
  createPost(data: Partial<AdminPost>) {
    return apiClient.post('/admin/posts/', data)
  },
  updatePost(id: number, data: Partial<AdminPost>) {
    return apiClient.patch(`/admin/posts/${id}/`, data)
  },
  deletePost(id: number) {
    return apiClient.delete(`/admin/posts/${id}/`)
  },

  // Categories
  getCategories() {
    return apiClient.get('/admin/categories/')
  },
  createCategory(data: { name: string; slug: string; description?: string; parent?: number | null; sort_order?: number }) {
    return apiClient.post('/admin/categories/', data)
  },
  updateCategory(id: number, data: Record<string, unknown>) {
    return apiClient.patch(`/admin/categories/${id}/`, data)
  },
  deleteCategory(id: number) {
    return apiClient.delete(`/admin/categories/${id}/`)
  },

  // Tags
  getTags() {
    return apiClient.get('/admin/tags/')
  },
  createTag(data: { name: string; slug: string; color?: string }) {
    return apiClient.post('/admin/tags/', data)
  },
  updateTag(id: number, data: Record<string, unknown>) {
    return apiClient.patch(`/admin/tags/${id}/`, data)
  },
  deleteTag(id: number) {
    return apiClient.delete(`/admin/tags/${id}/`)
  },

  // Comments
  getComments(params?: { page?: number }) {
    return apiClient.get('/admin/comments/', { params })
  },
  approveComment(id: number) {
    return apiClient.patch(`/admin/comments/${id}/`, { is_approved: true })
  },
  deleteComment(id: number) {
    return apiClient.delete(`/admin/comments/${id}/`)
  },

  // Site config
  getSiteConfig() {
    return apiClient.get('/admin/site-config/')
  },
  updateSiteConfig(data: Record<string, unknown>) {
    return apiClient.patch('/admin/site-config/', data)
  },

  // Image upload
  uploadImage(file: File) {
    const formData = new FormData()
    formData.append('image', file)
    return apiClient.post<{ url: string }>('/admin/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
