import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api/client';
import { tokenManager } from '../utils/token';

const AuthContext = createContext(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [initialized, setInitialized] = useState(false);

    // Initialize auth state from storage
    useEffect(() => {
        const initAuth = async () => {
            const token = tokenManager.getAccessToken();
            const savedUser = tokenManager.getUser();

            if (token && savedUser) {
                setUser(savedUser);

                // Verify token is still valid
                try {
                    const response = await api.auth.getCurrentUser();
                    setUser(response.data.user);
                    tokenManager.setUser(response.data.user);
                } catch (error) {
                    // Token invalid - clear auth
                    tokenManager.clearTokens();
                    setUser(null);
                }
            }

            setLoading(false);
            setInitialized(true);
        };

        initAuth();
    }, []);

    const login = async (email, password) => {
        const response = await api.auth.login(email, password);
        const { user, access_token, refresh_token } = response.data;

        tokenManager.setTokens(access_token, refresh_token);
        tokenManager.setUser(user);
        setUser(user);

        return user;
    };

    const register = async (email, password) => {
        const response = await api.auth.register(email, password);
        const { user, access_token, refresh_token } = response.data;

        tokenManager.setTokens(access_token, refresh_token);
        tokenManager.setUser(user);
        setUser(user);

        return user;
    };

    const logout = async () => {
        try {
            await api.auth.logout();
        } catch (error) {
            // Logout anyway even if API call fails
            console.error('Logout error:', error);
        } finally {
            tokenManager.clearTokens();
            setUser(null);
        }
    };

    const value = {
        user,
        loading,
        initialized,
        isAuthenticated: !!user,
        login,
        register,
        logout,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};