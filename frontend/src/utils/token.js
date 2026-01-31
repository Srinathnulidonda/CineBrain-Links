/**
 * Token management utilities
 * Handles secure storage and retrieval of JWT tokens
 */

const ACCESS_TOKEN_KEY = 'cinbrainlinks_access_token';
const REFRESH_TOKEN_KEY = 'cinbrainlinks_refresh_token';
const USER_KEY = 'cinbrainlinks_user';

export const tokenManager = {
    /**
     * Save authentication tokens
     */
    setTokens: (accessToken, refreshToken) => {
        if (accessToken) {
            localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
        }
        if (refreshToken) {
            localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
        }
    },

    /**
     * Get access token
     */
    getAccessToken: () => {
        return localStorage.getItem(ACCESS_TOKEN_KEY);
    },

    /**
     * Get refresh token
     */
    getRefreshToken: () => {
        return localStorage.getItem(REFRESH_TOKEN_KEY);
    },

    /**
     * Clear all auth data
     */
    clearTokens: () => {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    },

    /**
     * Save user data
     */
    setUser: (user) => {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
    },

    /**
     * Get user data
     */
    getUser: () => {
        const user = localStorage.getItem(USER_KEY);
        return user ? JSON.parse(user) : null;
    },

    /**
     * Check if user is authenticated
     */
    isAuthenticated: () => {
        return !!tokenManager.getAccessToken();
    }
};