// src/utils/auth.js
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signInWithRedirect,
    signInWithPopup,
    getRedirectResult,
    GoogleAuthProvider,
    signOut,
    sendEmailVerification,
    sendPasswordResetEmail,
    updateProfile,
    onAuthStateChanged,
    setPersistence,
    browserLocalPersistence,
    browserSessionPersistence
} from 'firebase/auth'
import { app } from '../config/firebase'
import axios from 'axios'

const auth = getAuth(app)
const googleProvider = new GoogleAuthProvider()

// Configure Google Provider
googleProvider.setCustomParameters({
    prompt: 'select_account'
})

// Configure axios
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'
axios.defaults.baseURL = API_BASE_URL
axios.defaults.timeout = 10000 // 10 second timeout

// Add response interceptor for better error handling
axios.interceptors.response.use(
    response => response,
    error => {
        // Log detailed error info in development
        if (import.meta.env.DEV) {
            console.error('API Error:', {
                url: error.config?.url,
                method: error.config?.method,
                status: error.response?.status,
                data: error.response?.data,
                message: error.message
            })
        }
        return Promise.reject(error)
    }
)

// Auth state management
let currentUser = null
let authStateListeners = []
let authInitialized = false
let authInitPromise = null

// Initialize auth persistence
const initializeAuth = async () => {
    if (authInitPromise) return authInitPromise

    authInitPromise = new Promise(async (resolve) => {
        try {
            // Set persistence based on remember me
            const rememberMe = localStorage.getItem('rememberMe') === 'true'
            await setPersistence(auth, rememberMe ? browserLocalPersistence : browserSessionPersistence)

            // Check for redirect result
            try {
                const result = await getRedirectResult(auth)
                if (result?.user) {
                    console.log('Redirect sign-in completed')
                    await handleSuccessfulAuth(result.user)

                    // Clear any redirect flags
                    sessionStorage.removeItem('auth_redirect_pending')

                    // Trigger navigation in the app
                    window.dispatchEvent(new CustomEvent('auth-redirect-success', {
                        detail: { user: currentUser }
                    }))
                }
            } catch (redirectError) {
                console.error('Redirect error:', redirectError)
                sessionStorage.removeItem('auth_redirect_pending')
                window.dispatchEvent(new CustomEvent('auth-redirect-error', {
                    detail: { error: redirectError }
                }))
            }

            authInitialized = true
            resolve(true)
        } catch (error) {
            console.error('Auth initialization error:', error)
            authInitialized = true
            resolve(false)
        }
    })

    return authInitPromise
}

// Initialize on import
initializeAuth()

// Helper function to handle successful authentication
async function handleSuccessfulAuth(firebaseUser) {
    if (!firebaseUser) return null

    try {
        const token = await firebaseUser.getIdToken()

        // Configure axios with token
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`

        // Attempt to sync with backend
        try {
            const response = await axios.get('/auth/me', {
                timeout: 5000,
                validateStatus: (status) => status < 500 // Don't throw on 4xx errors
            })

            if (response.status === 200 && response.data.success) {
                currentUser = {
                    ...response.data.data,
                    firebaseUser,
                    _syncedWithBackend: true
                }

                console.log('User synced with backend successfully')
            } else {
                // Backend returned error but not 5xx
                throw new Error(response.data?.error || 'Backend sync failed')
            }
        } catch (backendError) {
            // Determine if this is a critical error
            const isCriticalError = backendError.response?.status >= 500
            const errorDetails = {
                message: backendError.message,
                status: backendError.response?.status,
                data: backendError.response?.data,
                url: backendError.config?.url
            }

            // Log appropriately based on error severity
            if (isCriticalError) {
                console.error('Backend sync error:', errorDetails)
            } else {
                console.warn('Backend sync failed, using Firebase data:', errorDetails)
            }

            // Use Firebase data as fallback
            currentUser = {
                id: firebaseUser.uid,
                email: firebaseUser.email,
                name: firebaseUser.displayName,
                avatar_url: firebaseUser.photoURL,
                email_verified: firebaseUser.emailVerified,
                auth_provider: firebaseUser.providerData[0]?.providerId || 'password',
                created_at: firebaseUser.metadata.creationTime,
                last_login_at: firebaseUser.metadata.lastSignInTime,
                emergency_enabled: false, // Default value
                firebaseUser,
                // Metadata about sync status
                _syncedWithBackend: false,
                _syncError: errorDetails,
                _fallback: true
            }

            // Don't throw - continue with Firebase data
            console.info('Continuing with Firebase data (backend sync will retry on next request)')
        }

        return currentUser
    } catch (error) {
        console.error('Error handling auth:', error)
        // Clear any partial auth state
        currentUser = null
        delete axios.defaults.headers.common['Authorization']
        throw error
    }
}

// Listen to auth state changes
onAuthStateChanged(auth, async (firebaseUser) => {
    if (!authInitialized) return // Wait for initialization

    if (firebaseUser) {
        try {
            await handleSuccessfulAuth(firebaseUser)
        } catch (error) {
            console.error('Auth state change error:', error)
            currentUser = null
        }
    } else {
        currentUser = null
        delete axios.defaults.headers.common['Authorization']
    }

    // Notify listeners
    authStateListeners.forEach(listener => listener(currentUser))
})

// Refresh token periodically
let tokenRefreshInterval = null
const startTokenRefresh = () => {
    stopTokenRefresh()

    tokenRefreshInterval = setInterval(async () => {
        if (auth.currentUser) {
            try {
                const token = await auth.currentUser.getIdToken(true)
                axios.defaults.headers.common['Authorization'] = `Bearer ${token}`

                // Try to sync with backend again if previous sync failed
                if (currentUser && !currentUser._syncedWithBackend) {
                    console.log('Retrying backend sync...')
                    await handleSuccessfulAuth(auth.currentUser)
                }
            } catch (error) {
                console.error('Token refresh failed:', error)
            }
        }
    }, 55 * 60 * 1000) // Refresh every 55 minutes
}

const stopTokenRefresh = () => {
    if (tokenRefreshInterval) {
        clearInterval(tokenRefreshInterval)
        tokenRefreshInterval = null
    }
}

// Start token refresh when user is logged in
onAuthStateChanged(auth, (user) => {
    if (user) {
        startTokenRefresh()
    } else {
        stopTokenRefresh()
    }
})

export const AuthService = {
    // Ensure auth is initialized
    async ensureInitialized() {
        if (!authInitialized) {
            await initializeAuth()
        }
        return authInitialized
    },

    // Register with email/password
    async register({ email, password, name }) {
        try {
            await this.ensureInitialized()

            const userCredential = await createUserWithEmailAndPassword(auth, email, password)
            const user = userCredential.user

            if (name) {
                await updateProfile(user, { displayName: name })
            }

            // Send verification email
            await sendEmailVerification(user, {
                url: `${window.location.origin}/login?email=${encodeURIComponent(email)}`
            })

            const userData = await handleSuccessfulAuth(user)

            return {
                success: true,
                data: {
                    user: userData,
                    token: await user.getIdToken()
                }
            }
        } catch (error) {
            console.error('Registration error:', error)
            return {
                success: false,
                error: {
                    code: error.code,
                    message: this.getErrorMessage(error.code)
                }
            }
        }
    },

    // Login with email/password
    async login({ email, password, rememberMe = false }) {
        try {
            await this.ensureInitialized()

            // Set persistence based on remember me
            await setPersistence(
                auth,
                rememberMe ? browserLocalPersistence : browserSessionPersistence
            )

            // Store remember me preference
            localStorage.setItem('rememberMe', rememberMe.toString())

            const userCredential = await signInWithEmailAndPassword(auth, email, password)
            const userData = await handleSuccessfulAuth(userCredential.user)

            return {
                success: true,
                data: {
                    user: userData,
                    token: await userCredential.user.getIdToken()
                },
                message: 'Welcome back!'
            }
        } catch (error) {
            console.error('Login error:', error)
            return {
                success: false,
                error: {
                    code: error.code,
                    message: this.getErrorMessage(error.code)
                }
            }
        }
    },

    // Login with Google - Production grade with fallbacks
    async loginWithGoogle(preferRedirect = false) {
        try {
            await this.ensureInitialized()

            // Detect if we should use redirect
            const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
            const isIframe = window !== window.parent
            const shouldUseRedirect = preferRedirect || isMobile || isIframe

            if (shouldUseRedirect) {
                // Use redirect flow
                sessionStorage.setItem('auth_redirect_pending', 'true')
                await signInWithRedirect(auth, googleProvider)

                return {
                    success: true,
                    pending: true,
                    message: 'Redirecting to Google...'
                }
            }

            // Try popup flow
            try {
                const userCredential = await signInWithPopup(auth, googleProvider)
                const userData = await handleSuccessfulAuth(userCredential.user)

                return {
                    success: true,
                    data: {
                        user: userData,
                        token: await userCredential.user.getIdToken()
                    },
                    message: 'Welcome!'
                }
            } catch (popupError) {
                // If popup fails, try redirect as fallback
                if (
                    popupError.code === 'auth/popup-blocked' ||
                    popupError.code === 'auth/popup-closed-by-user' ||
                    popupError.code === 'auth/cancelled-popup-request'
                ) {
                    console.log('Popup blocked/closed, falling back to redirect')
                    return this.loginWithGoogle(true)
                }

                throw popupError
            }
        } catch (error) {
            console.error('Google login error:', error)

            // Don't treat user cancellation as an error
            if (
                error.code === 'auth/popup-closed-by-user' ||
                error.code === 'auth/cancelled-popup-request'
            ) {
                return {
                    success: false,
                    cancelled: true
                }
            }

            return {
                success: false,
                error: {
                    code: error.code,
                    message: this.getErrorMessage(error.code)
                }
            }
        }
    },

    // Logout
    async logout() {
        try {
            await signOut(auth)

            // Clear auth headers
            delete axios.defaults.headers.common['Authorization']

            // Clear storage
            localStorage.removeItem('rememberMe')
            sessionStorage.clear()

            // Stop token refresh
            stopTokenRefresh()

            currentUser = null

            return { success: true }
        } catch (error) {
            console.error('Logout error:', error)
            return {
                success: false,
                error: { message: 'Failed to sign out' }
            }
        }
    },

    // Password reset
    async resetPassword(email) {
        try {
            const actionCodeSettings = {
                url: `${window.location.origin}/login`,
                handleCodeInApp: false
            }

            await sendPasswordResetEmail(auth, email, actionCodeSettings)

            return {
                success: true,
                message: 'Password reset email sent. Please check your inbox.'
            }
        } catch (error) {
            console.error('Password reset error:', error)
            return {
                success: false,
                error: {
                    code: error.code,
                    message: this.getErrorMessage(error.code)
                }
            }
        }
    },

    // Resend verification email
    async resendVerificationEmail() {
        try {
            const user = auth.currentUser
            if (!user) {
                throw new Error('No user logged in')
            }

            const actionCodeSettings = {
                url: `${window.location.origin}/login?email=${encodeURIComponent(user.email)}`,
                handleCodeInApp: false
            }

            await sendEmailVerification(user, actionCodeSettings)

            return {
                success: true,
                message: 'Verification email sent'
            }
        } catch (error) {
            console.error('Resend verification error:', error)
            return {
                success: false,
                error: { message: 'Failed to send verification email' }
            }
        }
    },

    // Get current user
    getCurrentUser() {
        return currentUser
    },

    // Get Firebase user
    getFirebaseUser() {
        return auth.currentUser
    },

    // Check if authenticated
    isAuthenticated() {
        return !!auth.currentUser
    },

    // Check if backend is synced
    isBackendSynced() {
        return currentUser?._syncedWithBackend || false
    },

    // Get ID token
    async getIdToken(forceRefresh = false) {
        try {
            if (auth.currentUser) {
                return await auth.currentUser.getIdToken(forceRefresh)
            }
            return null
        } catch (error) {
            console.error('Get ID token error:', error)
            return null
        }
    },

    // Subscribe to auth state changes
    onAuthStateChange(callback) {
        authStateListeners.push(callback)

        // Call immediately with current state
        callback(currentUser)

        // Return unsubscribe function
        return () => {
            authStateListeners = authStateListeners.filter(listener => listener !== callback)
        }
    },

    // Manually retry backend sync
    async retryBackendSync() {
        if (auth.currentUser) {
            try {
                await handleSuccessfulAuth(auth.currentUser)
                return { success: true, synced: currentUser?._syncedWithBackend || false }
            } catch (error) {
                return { success: false, error: error.message }
            }
        }
        return { success: false, error: 'No authenticated user' }
    },

    // Error message mapping
    getErrorMessage(code) {
        const errorMessages = {
            'auth/email-already-in-use': 'This email is already registered. Please login instead.',
            'auth/invalid-email': 'Please enter a valid email address.',
            'auth/operation-not-allowed': 'This operation is not allowed. Please contact support.',
            'auth/weak-password': 'Password should be at least 6 characters long.',
            'auth/user-disabled': 'This account has been disabled. Please contact support.',
            'auth/user-not-found': 'No account found with this email. Please register first.',
            'auth/wrong-password': 'Incorrect password. Please try again.',
            'auth/invalid-credential': 'Invalid email or password. Please try again.',
            'auth/too-many-requests': 'Too many failed attempts. Please try again later.',
            'auth/network-request-failed': 'Network error. Please check your internet connection.',
            'auth/popup-closed-by-user': 'Sign-in was cancelled.',
            'auth/cancelled-popup-request': 'Another sign-in is already in progress.',
            'auth/account-exists-with-different-credential': 'An account already exists with this email using a different sign-in method.',
            'auth/popup-blocked': 'Sign-in popup was blocked by your browser. Please allow popups or try again.',
            'auth/requires-recent-login': 'This operation requires recent authentication. Please login again.',
            'auth/email-not-verified': 'Please verify your email before continuing.'
        }

        return errorMessages[code] || 'An unexpected error occurred. Please try again.'
    }
}

// Export auth instance for direct use if needed
export { auth }