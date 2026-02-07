// src/utils/auth.js

import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

// Create axios instance with default config
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true
})

// Token management
let accessToken = localStorage.getItem('access_token')
let refreshToken = localStorage.getItem('refresh_token')

// Add auth header to requests
api.interceptors.request.use(
    (config) => {
        if (accessToken) {
            config.headers.Authorization = `Bearer ${accessToken}`
        }
        return config
    },
    (error) => Promise.reject(error)
)

// Handle token refresh
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config

        if (error.response?.status === 401 && !originalRequest._retry && refreshToken) {
            originalRequest._retry = true

            try {
                const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
                    refresh_token: refreshToken
                })

                const { access_token, refresh_token } = response.data.data
                setTokens(access_token, refresh_token)

                originalRequest.headers.Authorization = `Bearer ${access_token}`
                return api(originalRequest)
            } catch (refreshError) {
                clearTokens()
                window.location.href = '/login'
                return Promise.reject(refreshError)
            }
        }

        return Promise.reject(error)
    }
)

// Token helpers
const setTokens = (access, refresh) => {
    accessToken = access
    refreshToken = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
}

const clearTokens = () => {
    accessToken = null
    refreshToken = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
}

export const AuthService = {
    // Register new user
    async register(email, password, metadata = {}) {
        try {
            const response = await api.post('/auth/register', {
                email,
                password,
                name: metadata.name || ''
            })

            if (response.data.success) {
                const { access_token, refresh_token, user } = response.data.data

                // Check if email confirmation is required
                if (!access_token && user?.email_confirmation_required) {
                    return {
                        data: {
                            user,
                            email_confirmation_required: true
                        },
                        error: null
                    }
                }

                // Full registration with immediate login
                if (access_token && refresh_token) {
                    setTokens(access_token, refresh_token)
                    localStorage.setItem('user', JSON.stringify(user))

                    return {
                        data: { session: { access_token }, user },
                        error: null
                    }
                }

                // Fallback - assume email confirmation needed
                return {
                    data: {
                        user: user || { email, email_confirmation_required: true },
                        email_confirmation_required: true
                    },
                    error: null
                }
            }

            return {
                data: null,
                error: { message: response.data.error?.message || 'Registration failed' }
            }
        } catch (error) {
            return {
                data: null,
                error: {
                    message: error.response?.data?.error?.message || 'Registration failed. Please try again.'
                }
            }
        }
    },

    // Login user
    async login(email, password) {
        try {
            const response = await api.post('/auth/login', {
                email,
                password
            })

            if (response.data.success) {
                const { access_token, refresh_token, user } = response.data.data
                setTokens(access_token, refresh_token)
                localStorage.setItem('user', JSON.stringify(user))

                return {
                    data: { session: { access_token }, user },
                    error: null
                }
            }

            return {
                data: null,
                error: { message: response.data.error?.message || 'Login failed' }
            }
        } catch (error) {
            return {
                data: null,
                error: {
                    message: error.response?.data?.error?.message || 'Login failed. Please check your credentials.'
                }
            }
        }
    },

    // Logout user
    async logout() {
        try {
            await api.post('/auth/logout')
        } catch (error) {
            console.error('Logout error:', error)
        } finally {
            clearTokens()
            window.location.href = '/login'
        }
    },

    // Get current session
    async getSession() {
        if (!accessToken) {
            return { session: null, user: null }
        }

        try {
            const response = await api.get('/auth/me')

            if (response.data.success) {
                const user = response.data.data
                localStorage.setItem('user', JSON.stringify(user))
                return {
                    session: { access_token: accessToken },
                    user
                }
            }

            return { session: null, user: null }
        } catch (error) {
            if (error.response?.status === 401) {
                clearTokens()
            }
            return { session: null, user: null }
        }
    },

    // Get current user
    async getUser() {
        const storedUser = localStorage.getItem('user')
        if (storedUser) {
            return JSON.parse(storedUser)
        }

        const { user } = await this.getSession()
        return user
    },

    // Update user profile
    async updateProfile(updates) {
        try {
            const response = await api.patch('/auth/me', updates)

            if (response.data.success) {
                const user = response.data.data
                localStorage.setItem('user', JSON.stringify(user))
                return { data: user, error: null }
            }

            return {
                data: null,
                error: { message: response.data.error?.message || 'Update failed' }
            }
        } catch (error) {
            return {
                data: null,
                error: {
                    message: error.response?.data?.error?.message || 'Update failed'
                }
            }
        }
    },

    // Request password reset
    async requestPasswordReset(email) {
        try {
            const response = await api.post('/auth/forgot-password', { email })

            return {
                success: response.data.success,
                message: response.data.message
            }
        } catch (error) {
            return {
                success: false,
                message: error.response?.data?.error?.message || 'Failed to send reset email'
            }
        }
    },

    // Reset password with token
    async resetPassword(token, password) {
        try {
            const response = await api.post('/auth/reset-password', {
                token,
                password
            })

            return {
                success: response.data.success,
                message: response.data.message
            }
        } catch (error) {
            return {
                success: false,
                message: error.response?.data?.error?.message || 'Failed to reset password'
            }
        }
    },

    // Change password
    async changePassword(currentPassword, newPassword) {
        try {
            const response = await api.post('/auth/change-password', {
                current_password: currentPassword,
                new_password: newPassword
            })

            return {
                success: response.data.success,
                message: response.data.message
            }
        } catch (error) {
            return {
                success: false,
                message: error.response?.data?.error?.message || 'Failed to change password'
            }
        }
    },

    // Google login (placeholder)
    async loginWithGoogle() {
        return {
            error: { message: 'AuthService.loginWithGoogle is not fully integrated' }
        }
    },

    // Backend verification (no longer needed with direct API)
    async verifyWithBackend() {
        return { error: null }
    }
}

// Export api instance for other services
export { api }