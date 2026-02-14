// src/components/dashboard/DashboardLayout.jsx
import React, { useState, useEffect } from 'react'; // Added React import
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import MobileMenu from './MobileMenu';
import ActivityBar from './ActivityBar';

export default function DashboardLayout({
    user,
    stats,
    activeView,
    onViewChange,
    onSearch,
    searchQuery,
    onAddLink,
    onOpenCommandPalette,
    children
}) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [viewMode, setViewMode] = useState('grid');
    const [collections, setCollections] = useState([
        { id: 1, name: 'Engineering', color: 'from-blue-600 to-blue-500', count: 432, emoji: '⚡' },
        { id: 2, name: 'Design', color: 'from-purple-600 to-purple-500', count: 234, emoji: '🎨' },
        { id: 3, name: 'Marketing', color: 'from-green-600 to-green-500', count: 156, emoji: '📈' },
        { id: 4, name: 'Docs', color: 'from-amber-600 to-amber-500', count: 89, emoji: '📚' },
        { id: 5, name: 'Research', color: 'from-red-600 to-red-500', count: 67, emoji: '🔬' },
    ]);

    // Detect mobile
    const [isMobile, setIsMobile] = useState(false);
    useEffect(() => {
        const checkMobile = () => setIsMobile(window.innerWidth < 768);
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    return (
        <div className="flex h-screen bg-black overflow-hidden">
            {/* Sidebar - Hidden on mobile */}
            {!isMobile && (
                <Sidebar
                    user={user}
                    stats={stats}
                    activeView={activeView}
                    onViewChange={onViewChange}
                    collections={collections}
                    onOpenCommandPalette={onOpenCommandPalette}
                />
            )}

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Header */}
                <Header
                    activeView={activeView}
                    stats={stats}
                    searchQuery={searchQuery}
                    onSearch={onSearch}
                    viewMode={viewMode}
                    onViewModeChange={setViewMode}
                    onAddLink={onAddLink}
                    onMenuClick={() => setIsMobileMenuOpen(true)}
                    onOpenCommandPalette={onOpenCommandPalette}
                    isMobile={isMobile}
                />

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto bg-black">
                    {React.Children.map(children, child =>
                        React.cloneElement(child, { viewMode })
                    )}
                </div>

                {/* Activity Bar */}
                <ActivityBar />
            </div>

            {/* Mobile Menu */}
            <AnimatePresence>
                {isMobileMenuOpen && (
                    <MobileMenu
                        isOpen={isMobileMenuOpen}
                        onClose={() => setIsMobileMenuOpen(false)}
                        user={user}
                        stats={stats}
                        activeView={activeView}
                        onViewChange={(view) => {
                            onViewChange(view);
                            setIsMobileMenuOpen(false);
                        }}
                        collections={collections}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}