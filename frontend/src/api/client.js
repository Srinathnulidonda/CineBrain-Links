import axios from 'axios';
import { tokenManager } from '../utils/token';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
console.log('🔗 API Base URL:', API_BASE_URL);

/**
 * Axios instance with automatic token injection
 */
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

/**
 * Request interceptor - add auth token
 */
apiClient.interceptors.request.use(
    (config) => {
        const token = tokenManager.getAccessToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

/**
 * Response interceptor - handle errors globally
 */
apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // Handle 401 Unauthorized
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            // Try to refresh token
            const refreshToken = tokenManager.getRefreshToken();

            if (refreshToken) {
                try {
                    const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {}, {
                        headers: {
                            Authorization: `Bearer ${refreshToken}`
                        }
                    });

                    const { access_token } = response.data;
                    tokenManager.setTokens(access_token, refreshToken);

                    // Retry original request with new token
                    originalRequest.headers.Authorization = `Bearer ${access_token}`;
                    return apiClient(originalRequest);
                } catch (refreshError) {
                    // Refresh failed - logout user
                    tokenManager.clearTokens();
                    window.location.href = '/login';
                    return Promise.reject(refreshError);
                }
            } else {
                // No refresh token - logout
                tokenManager.clearTokens();
                window.location.href = '/login';
            }
        }

        return Promise.reject(error);
    }
);

/**
 * API Service - all backend endpoints
 */
export const api = {
    // ============ AUTH ============
    auth: {
        register: (email, password) =>
            apiClient.post('/api/auth/register', { email, password }),

        login: (email, password) =>
            apiClient.post('/api/auth/login', { email, password }),

        logout: () =>
            apiClient.post('/api/auth/logout'),

        getCurrentUser: () =>
            apiClient.get('/api/auth/me'),

        forgotPassword: (email) =>
            apiClient.post('/api/auth/password/forgot', { email }),

        resetPassword: (token, password) =>
            apiClient.post('/api/auth/password/reset', { token, password }),

        changePassword: (currentPassword, newPassword) =>
            apiClient.post('/api/auth/password/change', {
                current_password: currentPassword,
                new_password: newPassword
            }),
    },

    // ============ LINKS ============
    links: {
        create: (data) =>
            apiClient.post('/api/links', data),

        getAll: (params = {}) =>
            apiClient.get('/api/links', { params }),

        getById: (id) =>
            apiClient.get(`/api/links/${id}`),

        update: (id, data) =>
            apiClient.put(`/api/links/${id}`, data),

        delete: (id) =>
            apiClient.delete(`/api/links/${id}`),

        toggle: (id) =>
            apiClient.post(`/api/links/${id}/toggle`),

        getStats: () =>
            apiClient.get('/api/links/stats'),

        checkSlug: (slug) =>
            apiClient.get('/api/links/check-slug', { params: { slug } }),
    },

    // ============ REDIRECT ============
    redirect: {
        preview: (slug) =>
            apiClient.get(`/${slug}/preview`),
    }
};

export default apiClient;