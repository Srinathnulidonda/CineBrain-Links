// frontend/src/pages/public/NotFound.jsx
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

export default function NotFound() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                className="text-center"
            >
                <div className="mb-8">
                    <span className="text-8xl font-bold text-savlink-primary/20 sm:text-9xl">
                        404
                    </span>
                </div>

                <h1 className="mb-4 text-2xl font-bold text-gray-900 sm:text-3xl">
                    Page not found
                </h1>

                <p className="mb-8 max-w-md text-gray-600">
                    Sorry, we couldn't find the page you're looking for. It might have
                    been moved or doesn't exist.
                </p>

                <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
                    <Link
                        to="/"
                        className="inline-flex items-center gap-2 rounded-xl bg-savlink-primary px-6 py-3 text-sm font-semibold text-white shadow-glow-sm transition-all duration-300 hover:bg-savlink-primary-light hover:shadow-glow"
                    >
                        <svg
                            className="h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={2}
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M10 19l-7-7m0 0l7-7m-7 7h18"
                            />
                        </svg>
                        Back to home
                    </Link>

                    <Link
                        to="/dashboard"
                        className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-6 py-3 text-sm font-semibold text-gray-700 transition-all duration-300 hover:border-savlink-primary/30 hover:bg-savlink-primary/5 hover:text-savlink-primary"
                    >
                        Go to dashboard
                    </Link>
                </div>
            </motion.div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3, duration: 0.6 }}
                className="absolute bottom-8"
            >
                <Link
                    to="/"
                    className="text-lg font-semibold text-gray-900 transition-colors hover:text-savlink-primary"
                >
                    Savlink
                </Link>
            </motion.div>
        </div>
    );
}