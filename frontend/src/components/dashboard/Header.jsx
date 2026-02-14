// src/components/dashboard/Header.jsx
import { motion } from 'framer-motion';

export default function Header({
    activeView,
    stats,
    searchQuery,
    onSearch,
    viewMode,
    onViewModeChange,
    onAddLink,
    onMenuClick,
    onOpenCommandPalette,
    isMobile
}) {
    const tabs = [
        { id: 'all', label: 'All', count: stats.all, icon: '🔗' },
        { id: 'recent', label: 'Recent', count: stats.recent, icon: '⏱️' },
        { id: 'starred', label: 'Starred', count: stats.starred, icon: '⭐' },
        { id: 'archive', label: 'Archive', count: stats.archive, icon: '📦' },
    ];

    const currentTab = tabs.find(t => t.id === activeView);

    return (
        <div className="border-b border-gray-900 bg-gray-950/50 px-3 sm:px-4 lg:px-6 py-3 sm:py-4">
            {/* Mobile Header */}
            {isMobile ? (
                <div>
                    <div className="flex items-center justify-between mb-3">
                        <button
                            onClick={onMenuClick}
                            className="p-1.5 text-gray-400"
                        >
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </button>
                        <h1 className="text-sm font-semibold text-white">
                            {currentTab?.label}
                        </h1>
                        <button
                            onClick={onOpenCommandPalette}
                            className="p-1.5 text-gray-400"
                        >
                            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                        </button>
                    </div>
                </div>
            ) : (
                /* Desktop Header */
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-base lg:text-lg font-semibold text-white flex items-center gap-2">
                            <span>{currentTab?.icon}</span>
                            {currentTab?.label}
                        </h1>
                        <p className="text-xs lg:text-sm text-gray-500">
                            {currentTab?.count.toLocaleString()} links
                        </p>
                    </div>
                    <div className="flex items-center gap-2 lg:gap-3">
                        {/* Search */}
                        <div className="relative hidden lg:block">
                            <svg className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <input
                                type="text"
                                placeholder="Search..."
                                value={searchQuery}
                                onChange={(e) => onSearch(e.target.value)}
                                className="w-48 xl:w-64 rounded-lg border border-gray-800 bg-gray-900 pl-10 pr-4 py-2 text-sm text-white placeholder-gray-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-all"
                            />
                        </div>

                        {/* View Options */}
                        <div className="hidden sm:flex items-center gap-1 rounded-lg border border-gray-800 p-1">
                            <button
                                onClick={() => onViewModeChange('grid')}
                                className={`rounded p-1.5 transition-all ${viewMode === 'grid' ? 'bg-gray-800 text-white' : 'text-gray-500 hover:text-white'}`}
                            >
                                <svg className="h-3.5 lg:h-4 w-3.5 lg:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                                </svg>
                            </button>
                            <button
                                onClick={() => onViewModeChange('list')}
                                className={`rounded p-1.5 transition-all ${viewMode === 'list' ? 'bg-gray-800 text-white' : 'text-gray-500 hover:text-white'}`}
                            >
                                <svg className="h-3.5 lg:h-4 w-3.5 lg:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                                </svg>
                            </button>
                        </div>

                        {/* Add Link */}
                        <button
                            onClick={onAddLink}
                            className="btn-primary flex items-center gap-2 text-xs lg:text-sm px-3 lg:px-5 py-1.5 lg:py-2.5"
                        >
                            <svg className="h-3.5 lg:h-4 w-3.5 lg:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                            </svg>
                            <span className="hidden sm:inline">Add</span>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}