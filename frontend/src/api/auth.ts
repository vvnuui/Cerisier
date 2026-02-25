import apiClient from './client'

export interface LoginData {
  username: string
  password: string
}

export interface TokenResponse {
  access: string
  refresh: string
}

export interface UserInfo {
  id: number
  username: string
  email: string
  role: string
  avatar: string
  bio: string
}

export const authApi = {
  login(data: LoginData) {
    return apiClient.post<TokenResponse>('/auth/token/', data)
  },
  refreshToken(refresh: string) {
    return apiClient.post<{ access: string }>('/auth/token/refresh/', { refresh })
  },
  getCurrentUser() {
    return apiClient.get<UserInfo>('/auth/me/')
  },
}
