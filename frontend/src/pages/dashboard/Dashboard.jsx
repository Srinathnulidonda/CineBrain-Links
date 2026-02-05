// frontend/src/pages/dashboard/Dashboard.jsx
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

export default function Dashboard() {
    return (
        <div className="min-h-screen bg-gray-50">
            {/* Placeholder Dashboard */}
            <div className="flex min-h-screen items-center justify-center p-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                    className="text-center"
                >
                    <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-savlink-primary/10">
                        <svg
                            className="h-8 w-8 text-savlink-primary"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={1.5}
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244"
                            />
                        </svg>
                    </div>
                    <h1 className="mb-2 text-2xl font-bold text-gray-900">
                        Dashboard coming soon
                    </h1>
                    <p className="mb-8 text-gray-600">
                        We're building something beautiful for you.
                    </p>
                    <Link
                        to="/"
                        className="btn btn-primary"
                    >
                        Back to home
                    </Link>
                </motion.div>
            </div>
        </div>
    );
}