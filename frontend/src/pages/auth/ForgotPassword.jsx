// src/pages/auth/ForgotPassword.jsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AuthService } from '../../utils/auth'
import toast from 'react-hot-toast'

export default function ForgotPassword() {
    const [email, setEmail] = useState('')
    const [loading, setLoading] = useState(false)
    const [submitted, setSubmitted] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)

        try {
            const result = await AuthService.requestPasswordReset(email)

            if (result.success) {
                setSubmitted(true)
                toast.success('Check your email for reset instructions')
            } else {
                toast.error(result.message || 'Failed to send reset email')
            }
        } catch (error) {
            toast.error('Something went wrong. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    if (submitted) {
        return (
            <div className="min-h-screen bg-black flex flex-col justify-center py-6 px-4 sm:py-12 sm:px-6 lg:px-8">
                <div className="sm:mx-auto sm:w-full sm:max-w-md">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-gray-950/50 backdrop-blur-xl border border-gray-900/50 py-8 px-4 shadow-2xl sm:rounded-lg sm:px-10"
                    >
                        <div className="text-center">
                            <svg
                                className="mx-auto h-12 w-12 text-green-400"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76"
                                />
                            </svg>
                            <h2 className="mt-4 text-2xl font-semibold text-white">Check your email</h2>
                            <p className="mt-2 text-sm text-gray-400">
                                We've sent password reset instructions to:
                            </p>
                            <p className="mt-1 text-sm font-medium text-primary">{email}</p>
                        </div>

                        <div className="mt-6 space-y-4">
                            <p className="text-xs text-gray-400 text-center">
                                Didn't receive the email? Check your spam folder or try again.
                            </p>

                            <div className="flex flex-col gap-3">
                                <button
                                    onClick={() => {
                                        setSubmitted(false)
                                        setEmail('')
                                    }}
                                    className="w-full py-2 px-4 border border-gray-700 rounded-md text-sm font-medium text-gray-300 bg-gray-900/50 hover:bg-gray-800 transition-all"
                                >
                                    Try another email
                                </button>

                                <Link
                                    to="/login"
                                    className="w-full py-2 px-4 text-center border border-transparent rounded-md text-sm font-medium text-white bg-primary hover:bg-primary-light transition-all"
                                >
                                    Back to login
                                </Link>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </div>
        )
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
                    <Link to="/" className="inline-flex items-center gap-2 group">
                        <div className="relative">
                            <div className="absolute inset-0 rounded-lg bg-primary/20 blur-lg group-hover:blur-xl transition-all duration-300" />
                            <div className="relative flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary-light shadow-lg">
                                <svg
                                    className="h-5 w-5 text-white"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    strokeWidth={2.5}
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244"
                                    />
                                </svg>
                            </div>
                        </div>
                        <span className="text-xl font-semibold text-white">Savlink</span>
                    </Link>

                    <h2 className="mt-6 text-2xl sm:text-3xl font-semibold text-white">
                        Reset your password
                    </h2>
                    <p className="mt-2 text-sm text-gray-400">
                        Enter your email and we'll send you a reset link
                    </p>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    className="mt-6 sm:mt-8"
                >
                    <div className="bg-gray-950/50 backdrop-blur-xl border border-gray-900/50 py-6 px-4 sm:py-8 sm:px-10 shadow-2xl rounded-lg">
                        <form className="space-y-6" onSubmit={handleSubmit}>
                            <div>
                                <label htmlFor="email" className="block text-sm font-medium text-gray-300">
                                    Email address
                                </label>
                                <div className="mt-1">
                                    <input
                                        id="email"
                                        name="email"
                                        type="email"
                                        autoComplete="email"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="appearance-none block w-full px-3 py-2 border border-gray-700 rounded-md placeholder-gray-500 text-white bg-gray-900/50 focus:outline-none focus:ring-primary focus:border-primary focus:z-10 text-sm sm:text-base"
                                        placeholder="Enter your email"
                                    />
                                </div>
                            </div>

                            <div>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full flex justify-center py-2.5 sm:py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-light focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary focus:ring-offset-gray-950 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? (
                                        <>
                                            <svg className="animate-spin -ml-1 mr-3 h-4 w-4 sm:h-5 sm:w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                            Sending...
                                        </>
                                    ) : (
                                        'Send reset link'
                                    )}
                                </button>
                            </div>

                            <div className="text-center text-sm">
                                <Link to="/login" className="text-primary hover:text-primary-light">
                                    Back to login
                                </Link>
                            </div>
                        </form>
                    </div>
                </motion.div>
            </div>
        </div>
    )
}