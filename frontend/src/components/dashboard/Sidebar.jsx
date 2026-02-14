// src/components/dashboard/Sidebar.jsx
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { AuthService } from '../../utils/auth';

export default function Sidebar({
    user,
    stats,
    activeView,
    onViewChange,
    collections,
    onOpenCommandPalette
}) {
    const navigate = useNavigate();

    const tabs = [
        { id: 'all', label: 'All', count: stats.all, icon: '🔗' },
        { id: 'recent', label: 'Recent', count: stats.recent, icon: '⏱️' },
        { id: 'starred', label: 'Starred', count: stats.starred, icon: '⭐' },
        { id: 'archive', label: 'Archive', count: stats.archive, icon: '📦' },
    ];

    const handleLogout = async () => {
        await AuthService.logout();
        navigate('/');
    };

    // Calculate storage percentage
    const storageUsed = 2.3; // GB
    const storageTotal = 10; // GB
    const storagePercentage = (storageUsed / storageTotal) * 100;

    return (
        <div className="w-56 lg:w-64 flex-shrink-0 border-r border-gray-900 bg-gray-950/50 flex flex-col">
            {/* User Profile */}
            <div className="border-b border-gray-900 p-3 lg:p-4">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <div className="h-9 lg:h-10 w-9 lg:w-10 rounded-lg bg-gradient-to-br from-primary to-primary-light flex items-center justify-center text-white text-sm font-semibold">
                            {user?.name ? user.name.substring(0, 2).toUpperCase() : 'US'}
                        </div>
                        <div className="absolute -bottom-0.5 -right-0.5 h-2.5 lg:h-3 w-2.5 lg:w-3 rounded-full bg-green-500 border-2 border-gray-950 animate-pulse"></div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white truncate">
                            {user?.name || 'User'}
                        </div>
                        <div className="text-xs text-gray-500">
                            Pro • {stats.all || 0} links
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="p-1.5 text-gray-500 hover:text-gray-400 transition-colors"
                        title="Sign out"
                    >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                    </button>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="p-3 lg:p-4">
                <button
                    onClick={onOpenCommandPalette}
                    className="w-full flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900/50 px-3 py-2 text-sm text-gray-400 hover:border-gray-700 hover:bg-gray-900 hover:text-white transition-all"
                >
                    <span className="flex items-center gap-2 text-xs lg:text-sm">
                        <svg className="h-3.5 lg:h-4 w-3.5 lg:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        Search...
                    </span>
                    <kbd className="text-[10px] lg:text-xs bg-gray-800 px-1.5 py-0.5 rounded font-mono">⌘K</kbd>
                </button>
            </div>

            {/* Navigation */}
            <nav className="px-3 pb-3">
                <div className="space-y-1">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => onViewChange(tab.id)}
                            className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-xs lg:text-sm font-medium transition-all ${activeView === tab.id
                                ? 'bg-primary/10 text-primary border border-primary/20'
                                : 'text-gray-400 hover:bg-gray-900 hover:text-white'
                                }`}
                        >
                            <span className="flex items-center gap-2">
                                <span className="text-sm lg:text-base">{tab.icon}</span>
                                {tab.label}
                            </span>
                            <span className={`text-[10px] lg:text-xs ${activeView === tab.id ? 'text-primary' : 'text-gray-600'
                                }`}>
                                {tab.count > 999 ? '999+' : tab.count}
                            </span>
                        </button>
                    ))}
                </div>
            </nav>

            {/* Collections */}
            <div className="flex-1 border-t border-gray-900 p-3 lg:p-4 overflow-y-auto">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-[10px] lg:text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        Collections
                    </h3>
                    <button className="text-gray-500 hover:text-gray-400 transition-colors">
                        <svg className="h-3.5 lg:h-4 w-3.5 lg:w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                        </svg>
                    </button>
                </div>
                <div className="space-y-1">
                    {collections.map((collection) => (
                        <Link
                            key={collection.id}
                            to={`/dashboard/collections/${collection.id}`}
                            className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs lg:text-sm text-gray-400 hover:bg-gray-900 hover:text-white transition-all group"
                        >
                            <span className="text-sm lg:text-base opacity-70 group-hover:opacity-100">
                                {collection.emoji}
                            </span>
                            <span className="flex-1 text-left truncate">{collection.name}</span>
                            <span className="text-[10px] lg:text-xs text-gray-600">{collection.count}</span>
                        </Link>
                    ))}
                </div>
            </div>
        </div>
    );
}