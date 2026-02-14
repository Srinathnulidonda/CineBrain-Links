// src/components/dashboard/MobileMenu.jsx
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

export default function MobileMenu({
    isOpen,
    onClose,
    user,
    stats,
    activeView,
    onViewChange,
    collections
}) {
    const tabs = [
        { id: 'all', label: 'All', count: stats.all, icon: '🔗' },
        { id: 'recent', label: 'Recent', count: stats.recent, icon: '⏱️' },
        { id: 'starred', label: 'Starred', count: stats.starred, icon: '⭐' },
        { id: 'archive', label: 'Archive', count: stats.archive, icon: '📦' },
    ];

    return (
        <>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
                onClick={onClose}
            />
            <motion.div
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                className="fixed left-0 top-0 z-50 h-full w-64 bg-gray-950 border-r border-gray-800 md:hidden overflow-y-auto"
            >
                {/* Header */}
                <div className="p-4 border-b border-gray-900">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-sm font-semibold text-white">Menu</h2>
                        <button
                            onClick={onClose}
                            className="text-gray-500"
                        >
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* User Info */}
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary to-primary-light flex items-center justify-center text-white text-sm font-semibold">
                            {user?.name ? user.name.substring(0, 2).toUpperCase() : 'US'}
                        </div>
                        <div>
                            <div className="text-sm font-medium text-white">{user?.name || 'User'}</div>
                            <div className="text-xs text-gray-500">{stats.all} links</div>
                        </div>
                    </div>
                </div>

                {/* Navigation Tabs */}
                <div className="p-4 border-b border-gray-900">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Views</h3>
                    <div className="space-y-1">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => onViewChange(tab.id)}
                                className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-sm ${activeView === tab.id
                                        ? 'bg-primary/10 text-primary'
                                        : 'text-gray-400 hover:bg-gray-900 hover:text-white'
                                    }`}
                            >
                                <span className="flex items-center gap-2">
                                    <span>{tab.icon}</span>
                                    <span>{tab.label}</span>
                                </span>
                                <span className="text-xs text-gray-600">({tab.count})</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Collections */}
                <div className="p-4">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Collections</h3>
                    <div className="space-y-1">
                        {collections.map((collection) => (
                            <button
                                key={collection.id}
                                onClick={onClose}
                                className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-gray-400 hover:bg-gray-900 hover:text-white"
                            >
                                <span>{collection.emoji}</span>
                                <span className="flex-1 text-left">{collection.name}</span>
                                <span className="text-xs text-gray-600">{collection.count}</span>
                            </button>
                        ))}
                    </div>
                </div>
            </motion.div>
        </>
    );
}