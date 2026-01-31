import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import Card from '../components/Card';
import Button from '../components/Button';
import Loader from '../components/Loader';
import LinkTable from '../components/LinkTable';

const Dashboard = () => {
    const { user } = useAuth();
    const [links, setLinks] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchData = async () => {
        setLoading(true);
        setError('');

        try {
            const [linksResponse, statsResponse] = await Promise.all([
                api.links.getAll({ sort: 'created_at', order: 'desc' }),
                api.links.getStats()
            ]);

            setLinks(linksResponse.data.links || []);
            setStats(statsResponse.data.stats || null);
        } catch (error) {
            console.error('Failed to fetch data:', error);
            setError('Failed to load dashboard data. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleDelete = async (id) => {
        try {
            await api.links.delete(id);
            return Promise.resolve();
        } catch (error) {
            console.error('Delete failed:', error);
            throw error;
        }
    };

    const handleToggle = async (id) => {
        try {
            await api.links.toggle(id);
            return Promise.resolve();
        } catch (error) {
            console.error('Toggle failed:', error);
            throw error;
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader size="lg" text="Loading your dashboard..." />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
                    <p className="text-gray-600">Welcome back, {user?.email}</p>
                </div>

                {/* Error State */}
                {error && (
                    <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                        <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        <div>
                            <p className="text-sm text-red-800">{error}</p>
                            <button onClick={fetchData} className="text-sm text-red-700 underline mt-1">
                                Try again
                            </button>
                        </div>
                    </div>
                )}

                {/* Stats Cards */}
                {stats && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <Card className="bg-gradient-to-br from-primary-500 to-primary-600 text-white">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-primary-100 text-sm font-medium mb-1">Total Links</p>
                                    <p className="text-3xl font-bold">{stats.total_links}</p>
                                </div>
                                <div className="w-12 h-12 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                                    </svg>
                                </div>
                            </div>
                        </Card>

                        <Card className="bg-gradient-to-br from-green-500 to-green-600 text-white">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-green-100 text-sm font-medium mb-1">Active Links</p>
                                    <p className="text-3xl font-bold">{stats.active_links}</p>
                                </div>
                                <div className="w-12 h-12 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                </div>
                            </div>
                        </Card>

                        <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-blue-100 text-sm font-medium mb-1">Total Clicks</p>
                                    <p className="text-3xl font-bold">{stats.total_clicks}</p>
                                </div>
                                <div className="w-12 h-12 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                    </svg>
                                </div>
                            </div>
                        </Card>

                        <Card className="bg-gradient-to-br from-orange-500 to-orange-600 text-white">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-orange-100 text-sm font-medium mb-1">Expiring Soon</p>
                                    <p className="text-3xl font-bold">{stats.expiring_soon}</p>
                                </div>
                                <div className="w-12 h-12 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                </div>
                            </div>
                        </Card>
                    </div>
                )}

                {/* Quick Actions */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">Your Links</h2>
                    <Link to="/create">
                        <Button variant="primary" size="md">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            Create New Link
                        </Button>
                    </Link>
                </div>

                {/* Links Table */}
                <LinkTable
                    links={links}
                    onDelete={handleDelete}
                    onToggle={handleToggle}
                    onRefresh={fetchData}
                />
            </div>
        </div>
    );
};

export default Dashboard;