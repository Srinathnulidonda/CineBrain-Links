import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useState } from 'react';
import Button from './Button';

const Navbar = () => {
    const { isAuthenticated, user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const isActive = (path) => location.pathname === path;

    return (
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16">
                    {/* Logo */}
                    <Link to="/" className="flex items-center gap-2 group">
                        <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-secondary-600 rounded-lg flex items-center justify-center group-hover:scale-105 transition-transform">
                            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                            </svg>
                        </div>
                        <span className="text-xl font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                            CinBrainLinks
                        </span>
                    </Link>

                    {/* Desktop Navigation */}
                    <div className="hidden md:flex items-center gap-6">
                        {isAuthenticated ? (
                            <>
                                <Link
                                    to="/dashboard"
                                    className={`text-sm font-medium transition-colors ${isActive('/dashboard') ? 'text-primary-600' : 'text-gray-600 hover:text-gray-900'
                                        }`}
                                >
                                    Dashboard
                                </Link>
                                <Link
                                    to="/create"
                                    className={`text-sm font-medium transition-colors ${isActive('/create') ? 'text-primary-600' : 'text-gray-600 hover:text-gray-900'
                                        }`}
                                >
                                    Create Link
                                </Link>

                                {/* User Menu */}
                                <div className="flex items-center gap-3 pl-3 border-l border-gray-200">
                                    <div className="text-right">
                                        <p className="text-sm font-medium text-gray-900">{user?.email}</p>
                                    </div>
                                    <Button variant="ghost" size="sm" onClick={handleLogout}>
                                        Logout
                                    </Button>
                                </div>
                            </>
                        ) : (
                            <div className="flex items-center gap-3">
                                <Link to="/login">
                                    <Button variant="ghost" size="sm">Login</Button>
                                </Link>
                                <Link to="/register">
                                    <Button variant="primary" size="sm">Get Started</Button>
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Mobile menu button */}
                    <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="md:hidden p-2 rounded-lg hover:bg-gray-100"
                    >
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            {mobileMenuOpen ? (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            ) : (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            )}
                        </svg>
                    </button>
                </div>

                {/* Mobile Menu */}
                {mobileMenuOpen && (
                    <div className="md:hidden py-4 border-t border-gray-200 animate-fade-in">
                        {isAuthenticated ? (
                            <div className="flex flex-col gap-3">
                                <p className="text-sm font-medium text-gray-900 px-4">{user?.email}</p>
                                <Link
                                    to="/dashboard"
                                    className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
                                    onClick={() => setMobileMenuOpen(false)}
                                >
                                    Dashboard
                                </Link>
                                <Link
                                    to="/create"
                                    className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
                                    onClick={() => setMobileMenuOpen(false)}
                                >
                                    Create Link
                                </Link>
                                <button
                                    onClick={() => {
                                        handleLogout();
                                        setMobileMenuOpen(false);
                                    }}
                                    className="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg text-left"
                                >
                                    Logout
                                </button>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-3 px-4">
                                <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                                    <Button variant="ghost" size="md" fullWidth>Login</Button>
                                </Link>
                                <Link to="/register" onClick={() => setMobileMenuOpen(false)}>
                                    <Button variant="primary" size="md" fullWidth>Get Started</Button>
                                </Link>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </nav>
    );
};

export default Navbar;