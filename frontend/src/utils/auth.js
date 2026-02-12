// src/utils/auth.js - COMPLETE FIXED VERSION
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

// Production API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'
axios.defaults.baseURL = API_BASE_URL
axios.defaults.timeout = 30000

// Retry configuration
const MAX_RETRIES = 3
const RETRY_DELAY = 1000

// Request interceptor
axios.interceptors.request.use(
    config => {
        config.metadata = { startTime: new Date() }
        return config
    },
    error => Promise.reject(error)
)

// Response interceptor with enhanced retry logic
axios.interceptors.response.use(
    response => {
        const duration = new Date() - response.config.metadata.startTime
        if (duration > 10000) {
            console.warn(`Slow API call: ${response.config.url} took ${duration}ms`)
        }
        return response
    },
    async error => {
        const config = error.config

        if (!config || !config.retry) {
            config.retry = 0
        }

        // Retry on timeout or network errors
        const shouldRetry =
            config.retry < MAX_RETRIES &&
            (error.code === 'ECONNABORTED' ||
                error.code === 'NETWORK_ERROR' ||
                error.message.includes('timeout'))

        if (shouldRetry) {
            config.retry++
            console.log(`Retrying request (${config.retry}/${MAX_RETRIES}): ${config.url}`)

            // Exponential backoff
            await new Promise(resolve =>
                setTimeout(resolve, RETRY_DELAY * Math.pow(2, config.retry - 1))
            )

            // Increase timeout for retries
            config.timeout = config.timeout * 1.5

            return axios(config)
        }

        return Promise.reject(error)
    }
)

// Enhanced warmup for cold starts
let warmupInterval = null
let isWarmedUp = false

const startWarmup = () => {
    if (warmupInterval) return

    const warmup = async () => {
        try {
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), 3000)

            const response = await fetch(`${API_BASE_URL}/health`, {
                method: 'GET',
                mode: 'cors',
                signal: controller.signal
            })

            clearTimeout(timeoutId)

            if (response.ok) {
                isWarmedUp = true
                console.log('✅ Backend warmed up')
            }
        } catch (e) {
            // Silent fail
        }
    }

    // Aggressive initial warmup
    warmup() // Immediate
    setTimeout(warmup, 2000)  // 2 seconds
    setTimeout(warmup, 5000)  // 5 seconds
    setTimeout(warmup, 10000) // 10 seconds

    // Regular keepalive
    warmupInterval = setInterval(warmup, 2 * 60 * 1000) // Every 2 minutes
}

const stopWarmup = () => {
    if (warmupInterval) {
        clearInterval(warmupInterval)
        warmupInterval = null
    }
}

// Auth state management
let currentUser = null
let authStateListeners = []
let authInitialized = false
let authInitPromise = null

// Check storage availability
const checkStorage = (storage) => {
    try {
        const test = '__test__'
        storage.setItem(test, test)
        storage.removeItem(test)
        return true
    } catch (e) {
        return false
    }
}

const hasSessionStorage = checkStorage(sessionStorage)
const hasLocalStorage = checkStorage(localStorage)

// Initialize auth with storage fallback
const initializeAuth = async () => {
    if (authInitPromise) return authInitPromise

    authInitPromise = new Promise(async (resolve) => {
        try {
            // Determine persistence strategy
            let persistence = browserLocalPersistence // Default to local

            if (hasLocalStorage && hasSessionStorage) {
                const rememberMe = localStorage.getItem('rememberMe') === 'true'
                persistence = rememberMe ? browserLocalPersistence : browserSessionPersistence
            }

            await setPersistence(auth, persistence)

            // Handle redirect result with enhanced error handling
            try {
                const result = await getRedirectResult(auth)
                if (result?.user) {
                    console.log('🔄 Redirect sign-in completed')
                    await handleSuccessfulAuth(result.user)

                    if (hasSessionStorage) {
                        sessionStorage.removeItem('auth_redirect_pending')
                    }

                    window.dispatchEvent(new CustomEvent('auth-redirect-success', {
                        detail: { user: currentUser }
                    }))
                }
            } catch (redirectError) {
                if (redirectError.code === 'auth/missing-initial-state' ||
                    redirectError.code === 'auth/web-storage-unsupported') {
                    console.warn('⚠️ Storage issue detected, checking current auth state')

                    // Wait a bit for auth to settle
                    await new Promise(resolve => setTimeout(resolve, 1000))

                    if (auth.currentUser) {
                        await handleSuccessfulAuth(auth.currentUser)
                    }
                } else {
                    console.error('Redirect error:', redirectError)
                    if (hasSessionStorage) {
                        sessionStorage.removeItem('auth_redirect_pending')
                    }
                }
            }

            authInitialized = true

            // Start warmup
            if (import.meta.env.PROD) {
                startWarmup()
            }

            resolve(true)
        } catch (error) {
            console.error('Auth initialization error:', error)
            authInitialized = true
            resolve(false)
        }
    })

    return authInitPromise
}

// Initialize immediately
initializeAuth()

// Enhanced auth handler with progressive timeouts
async function handleSuccessfulAuth(firebaseUser) {
    if (!firebaseUser) return null

    try {
        const token = await firebaseUser.getIdToken()
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`

        // Set Firebase data immediately for UI
        currentUser = {
            id: firebaseUser.uid,
            email: firebaseUser.email,
            name: firebaseUser.displayName,
            avatar_url: firebaseUser.photoURL,
            email_verified: firebaseUser.emailVerified,
            auth_provider: firebaseUser.providerData[0]?.providerId || 'password',
            created_at: firebaseUser.metadata.creationTime,
            last_login_at: firebaseUser.metadata.lastSignInTime,
            firebaseUser,
            _syncedWithBackend: false,
            _syncPending: true
        }

        // Notify listeners immediately
        authStateListeners.forEach(listener => listener(currentUser))

        // Warm up backend if cold
        if (!isWarmedUp && import.meta.env.PROD) {
            console.log('⏳ Warming up backend...')
            try {
                await axios.get('/health', {
                    timeout: 5000,
                    validateStatus: () => true
                })
                isWarmedUp = true
            } catch (e) {
                console.log('⚠️ Backend is cold, will retry...')
            }
        }

        // Backend sync with progressive timeout
        let syncSuccess = false
        const maxAttempts = 3
        const baseTimeout = isWarmedUp ? 10000 : 20000

        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                console.log(`🔄 Syncing with backend (attempt ${attempt}/${maxAttempts})...`)

                const timeout = baseTimeout + (attempt - 1) * 10000

                const response = await axios.get('/auth/me', {
                    timeout,
                    validateStatus: (status) => status < 500
                })

                if (response.status === 200 && response.data.success) {
                    currentUser = {
                        ...response.data.data,
                        firebaseUser,
                        _syncedWithBackend: true,
                        _syncPending: false
                    }

                    console.log('✅ Backend sync successful')
                    syncSuccess = true
                    isWarmedUp = true

                    // Notify listeners with synced data
                    authStateListeners.forEach(listener => listener(currentUser))
                    break
                }
            } catch (syncError) {
                console.warn(`Sync attempt ${attempt} failed:`, syncError.message)

                if (attempt < maxAttempts) {
                    // Wait before retry with exponential backoff
                    await new Promise(resolve =>
                        setTimeout(resolve, Math.min(1000 * Math.pow(2, attempt), 5000))
                    )
                }
            }
        }

        if (!syncSuccess) {
            console.warn('⚠️ Using Firebase data only (backend sync failed)')
            currentUser._syncedWithBackend = false
            currentUser._syncPending = false
            currentUser._syncError = 'Backend sync failed after retries'

            // Still notify listeners
            authStateListeners.forEach(listener => listener(currentUser))
        }

        return currentUser
    } catch (error) {
        console.error('❌ Auth handler error:', error)
        currentUser = null
        delete axios.defaults.headers.common['Authorization']
        throw error
    }
}

// Listen to auth state changes
onAuthStateChanged(auth, async (firebaseUser) => {
    if (!authInitialized) return

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
        stopWarmup()
    }

    authStateListeners.forEach(listener => listener(currentUser))
})

// Token refresh with retry
let tokenRefreshInterval = null
const startTokenRefresh = () => {
    stopTokenRefresh()

    tokenRefreshInterval = setInterval(async () => {
        if (auth.currentUser) {
            try {
                const token = await auth.currentUser.getIdToken(true)
                axios.defaults.headers.common['Authorization'] = `Bearer ${token}`

                // Retry backend sync if needed
                if (currentUser && !currentUser._syncedWithBackend) {
                    try {
                        const response = await axios.get('/auth/me', { timeout: 15000 })
                        if (response.data.success) {
                            currentUser = {
                                ...response.data.data,
                                firebaseUser: auth.currentUser,
                                _syncedWithBackend: true
                            }
                            authStateListeners.forEach(listener => listener(currentUser))
                        }
                    } catch (e) {
                        // Silent fail
                    }
                }
            } catch (error) {
                console.error('Token refresh failed:', error)
            }
        }
    }, 45 * 60 * 1000) // 45 minutes
}

const stopTokenRefresh = () => {
    if (tokenRefreshInterval) {
        clearInterval(tokenRefreshInterval)
        tokenRefreshInterval = null
    }
}

// Auto-start token refresh
onAuthStateChanged(auth, (user) => {
    if (user) {
        startTokenRefresh()
        if (import.meta.env.PROD) {
            startWarmup()
        }
    } else {
        stopTokenRefresh()
        stopWarmup()
    }
})

export const AuthService = {
    async ensureInitialized() {
        if (!authInitialized) {
            await initializeAuth()
        }
        return authInitialized
    },

    async register({ email, password, name }) {
        try {
            await this.ensureInitialized()

            const userCredential = await createUserWithEmailAndPassword(auth, email, password)
            const user = userCredential.user

            if (name) {
                await updateProfile(user, { displayName: name })
            }

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

    async login({ email, password, rememberMe = false }) {
        try {
            await this.ensureInitialized()

            // Set persistence
            const persistence = rememberMe ? browserLocalPersistence : browserSessionPersistence
            await setPersistence(auth, persistence)

            if (hasLocalStorage) {
                localStorage.setItem('rememberMe', rememberMe.toString())
            }

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

    async loginWithGoogle(forceRedirect = false) {
        try {
            await this.ensureInitialized()

            // Always use redirect on mobile or if storage is problematic
            const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
            const hasStorageIssues = !hasSessionStorage || !hasLocalStorage
            const isIframe = window !== window.parent

            // Check for COOP issues
            let hasCOOPIssues = false
            try {
                hasCOOPIssues = window.crossOriginIsolated === true
            } catch (e) {
                // Can't detect, assume false
            }

            const shouldUseRedirect = forceRedirect || isMobile || hasStorageIssues ||
                isIframe || hasCOOPIssues

            if (shouldUseRedirect) {
                console.log('Using redirect flow for Google sign-in')
                if (hasSessionStorage) {
                    sessionStorage.setItem('auth_redirect_pending', 'true')
                }
                await signInWithRedirect(auth, googleProvider)
                return {
                    success: true,
                    pending: true,
                    message: 'Redirecting to Google...'
                }
            }

            // Try popup
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
                // Fallback to redirect if popup fails
                if (popupError.code === 'auth/popup-blocked' ||
                    popupError.code === 'auth/cancelled-popup-request' ||
                    popupError.code === 'auth/popup-closed-by-user') {

                    if (popupError.code === 'auth/popup-closed-by-user') {
                        return { success: false, cancelled: true }
                    }

                    console.log('Popup failed, using redirect')
                    return this.loginWithGoogle(true)
                }

                throw popupError
            }
        } catch (error) {
            console.error('Google login error:', error)

            if (error.code === 'auth/popup-closed-by-user' ||
                error.code === 'auth/cancelled-popup-request') {
                return { success: false, cancelled: true }
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

    async logout() {
        try {
            await signOut(auth)
            delete axios.defaults.headers.common['Authorization']

            if (hasLocalStorage) {
                localStorage.removeItem('rememberMe')
            }
            if (hasSessionStorage) {
                sessionStorage.clear()
            }

            stopTokenRefresh()
            stopWarmup()
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

    async resetPassword(email) {
        try {
            await sendPasswordResetEmail(auth, email, {
                url: `${window.location.origin}/login`,
                handleCodeInApp: false
            })

            return {
                success: true,
                message: 'Password reset email sent.'
            }
        } catch (error) {
            return {
                success: false,
                error: {
                    code: error.code,
                    message: this.getErrorMessage(error.code)
                }
            }
        }
    },

    async resendVerificationEmail() {
        try {
            const user = auth.currentUser
            if (!user) throw new Error('No user logged in')

            await sendEmailVerification(user, {
                url: `${window.location.origin}/login?email=${encodeURIComponent(user.email)}`
            })

            return {
                success: true,
                message: 'Verification email sent'
            }
        } catch (error) {
            return {
                success: false,
                error: { message: 'Failed to send verification email' }
            }
        }
    },

    getCurrentUser() {
        return currentUser
    },

    getFirebaseUser() {
        return auth.currentUser
    },

    isAuthenticated() {
        return !!auth.currentUser
    },

    isBackendSynced() {
        return currentUser?._syncedWithBackend || false
    },

    getSyncStatus() {
        if (!currentUser) return { synced: false, reason: 'not_authenticated' }

        return {
            synced: currentUser._syncedWithBackend || false,
            pending: currentUser._syncPending || false,
            error: currentUser._syncError || null
        }
    },

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

    onAuthStateChange(callback) {
        authStateListeners.push(callback)
        callback(currentUser)

        return () => {
            authStateListeners = authStateListeners.filter(listener => listener !== callback)
        }
    },

    async retryBackendSync() {
        if (auth.currentUser) {
            try {
                console.log('Manual backend sync retry...')
                await handleSuccessfulAuth(auth.currentUser)
                return {
                    success: true,
                    synced: currentUser?._syncedWithBackend || false
                }
            } catch (error) {
                return { success: false, error: error.message }
            }
        }
        return { success: false, error: 'No authenticated user' }
    },

    getErrorMessage(code) {
        const errorMessages = {
            'auth/email-already-in-use': 'This email is already registered.',
            'auth/invalid-email': 'Please enter a valid email address.',
            'auth/operation-not-allowed': 'This operation is not allowed.',
            'auth/weak-password': 'Password should be at least 6 characters.',
            'auth/user-disabled': 'This account has been disabled.',
            'auth/user-not-found': 'No account found with this email.',
            'auth/wrong-password': 'Incorrect password.',
            'auth/invalid-credential': 'Invalid email or password.',
            'auth/too-many-requests': 'Too many failed attempts. Try again later.',
            'auth/network-request-failed': 'Network error. Check your connection.',
            'auth/popup-closed-by-user': 'Sign-in was cancelled.',
            'auth/cancelled-popup-request': 'Another sign-in in progress.',
            'auth/account-exists-with-different-credential': 'Account exists with different sign-in method.',
            'auth/popup-blocked': 'Sign-in popup blocked. Please allow popups.',
            'auth/requires-recent-login': 'Please login again.',
            'auth/missing-initial-state': 'Session storage issue detected. Please try again.'
        }

        return errorMessages[code] || 'An error occurred. Please try again.'
    }
}

export { auth }