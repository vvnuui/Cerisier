import apiClient from './client'

export interface Category {
  id: number
  name: string
  slug: string
  description: string
  children: Category[]
  post_count: number
}

export interface Tag {
  id: number
  name: string
  slug: string
  color: string
  post_count: number
}

export interface Post {
  id: number
  title: string
  slug: string
  excerpt: string
  cover_image: string | null
  category: Category | null
  tags: Tag[]
  status: string
  is_pinned: boolean
  view_count: number
  like_count: number
  author_name: string
  created_at: string
  published_at: string | null
}

export interface PostDetail extends Post {
  content: string
  content_markdown: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export const blogApi = {
  getPosts(params?: { page?: number; category?: string; tag?: string }) {
    return apiClient.get<PaginatedResponse<Post>>('/posts/', { params })
  },

  getPost(slug: string) {
    return apiClient.get<PostDetail>(`/posts/${slug}/`)
  },

  getCategories() {
    return apiClient.get<Category[]>('/categories/')
  },

  getTags() {
    return apiClient.get<Tag[]>('/tags/')
  },

  getArchives() {
    return apiClient.get<Record<string, Array<{ title: string; slug: string; published_at: string }>>>('/archives/')
  },

  getComments(slug: string) {
    return apiClient.get(`/posts/${slug}/comments/`)
  },

  createComment(slug: string, data: { content: string; nickname?: string; email?: string; parent?: number }) {
    return apiClient.post(`/posts/${slug}/comments/create/`, data)
  },

  getSiteConfig() {
    return apiClient.get('/site-config/')
  },
}
