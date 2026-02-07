// src/pages/auth/ResetPassword.jsx
import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AuthService } from '../../utils/auth'
import toast from 'react-hot-toast'

export default function ResetPassword() {
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [showPassword, setShowPassword] = useState(false)
    const [passwordValidation, setPasswordValidation] = useState({
        minLength: false,
        hasUpper: false,
        hasLower: false,
        hasNumber: false,
        hasSpecial: false
    })

    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const token = searchParams.get('token')

    useEffect(() => {
        if (!token) {
            toast.error('Invalid reset link')
            navigate('/login')
        }
    }, [token, navigate])

    useEffect(() => {
        // Validate password in real-time
        setPasswordValidation({
            minLength: password.length >= 8,
            hasUpper: /[A-Z]/.test(password),
            hasLower: /[a-z]/.test(password),
            hasNumber: /\d/.test(password),
            hasSpecial: /[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;'`~]/.test(password)
        })
    }, [password])

    const isPasswordValid = Object.values(passwordValidation).every(Boolean)
    const passwordsMatch = password === confirmPassword

    const handleSubmit = async (e) => {
        e.preventDefault()

        if (!isPasswordValid) {
            toast.error('Please ensure your password meets all requirements')
            return
        }

        if (!passwordsMatch) {
            toast.error('Passwords do not match')
            return
        }

        setLoading(true)

        try {
            const result = await AuthService.resetPassword(token, password)

            if (result.success) {
                toast.success('Password reset successfully!')
                navigate('/login')
            } else {
                toast.error(result.message || 'Failed to reset password')
            }
        } catch (error) {
            toast.error('Something went wrong. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-black flex flex-col justify-center py-6 px-4 sm:py-12 sm:px-6 lg:px-8">
            {/* Background Effects */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute left-1/2 top-1/4 -translate-x-1/2 -translate-y-1/2">
                    <div className="h-[300px] w-[300px] sm:h-[400px] sm:w-[400px] rounded-full bg-primary/10 blur-[100px] sm:blur-[128px]" />
                </div>
            </div>

            <div className="relative sm:mx-auto sm:w-full sm:max-w-md">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="text-center"
                >
                    <h2 className="text-2xl sm:text-3xl font-semibold text-white">
                        Create new password
                    </h2>
                    <p className="mt-2 text-sm text-gray-400">
                        Your new password must be different from previous passwords
                    </p>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    className="mt-6 sm:mt-8"
                >
                    <div className="bg-gray-950/50 backdrop-blur-xl border border-gray-900/50 py-6 px-4 sm:py-8 sm:px-10 shadow-2xl rounded-lg">
                        <form className="space-y-5 sm:space-y-6" onSubmit={handleSubmit}>
                            <div>
                                <label htmlFor="password" className="block text-sm font-medium text-gray-300">
                                    New password
                                </label>
                                <div className="mt-1 relative">
                                    <input
                                        id="password"
                                        name="password"
                                        type={showPassword ? 'text' : 'password'}
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="appearance-none block w-full px-3 py-2 pr-10 border border-gray-700 rounded-md placeholder-gray-500 text-white bg-gray-900/50 focus:outline-none focus:ring-primary focus:border-primary focus:z-10 text-sm sm:text-base"
                                        placeholder="Create new password"
                                    />
                                    <button
                                        type="button"
                                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                                        onClick={() => setShowPassword(!showPassword)}
                                    >
                                        {showPassword ? (
                                            <svg className="h-4 w-4 sm:h-5 sm:w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                                            </svg>
                                        ) : (
                                            <svg className="h-4 w-4 sm:h-5 sm:w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                            </svg>
                                        )}
                                    </button>
                                </div>

                                {/* Password Requirements */}
                                {password && (
                                    <div className="mt-2 space-y-1">
                                        <div className="text-xs text-gray-400">Password must contain:</div>
                                        <div className="grid grid-cols-1 gap-1 text-xs">
                                            {Object.entries({
                                                minLength: 'At least 8 characters',
                                                hasUpper: 'One uppercase letter',
                                                hasLower: 'One lowercase letter',
                                                hasNumber: 'One number',
                                                hasSpecial: 'One special character'
                                            }).map(([key, label]) => (
                                                <div key={key} className={`flex items-center gap-1 ${passwordValidation[key] ? 'text-green-400' : 'text-gray-500'}`}>
                                                    <svg className="h-3 w-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                                    </svg>
                                                    {label}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div>
                                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300">
                                    Confirm new password
                                </label>
                                <div className="mt-1">
                                    <input
                                        id="confirmPassword"
                                        name="confirmPassword"
                                        type="password"
                                        required
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className={`appearance-none block w-full px-3 py-2 border rounded-md placeholder-gray-500 text-white bg-gray-900/50 focus:outline-none focus:ring-primary focus:z-10 text-sm sm:text-base ${confirmPassword && !passwordsMatch
                                            ? 'border-red-500 focus:border-red-500'
                                            : 'border-gray-700 focus:border-primary'
                                            }`}
                                        placeholder="Confirm new password"
                                    />
                                    {confirmPassword && !passwordsMatch && (
                                        <p className="mt-1 text-xs text-red-400">Passwords do not match</p>
                                    )}
                                </div>
                            </div>

                            <div>
                                <button
                                    type="submit"
                                    disabled={loading || !isPasswordValid || !passwordsMatch}
                                    className="w-full flex justify-center py-2.5 sm:py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-light focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary focus:ring-offset-gray-950 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? (
                                        <>
                                            <svg className="animate-spin -ml-1 mr-3 h-4 w-4 sm:h-5 sm:w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                            Resetting...
                                        </>
                                    ) : (
                                        'Reset password'
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </motion.div>
            </div>
        </div>
    )
}