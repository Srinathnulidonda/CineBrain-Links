import { useState } from 'react';
import Button from './Button';
import Card from './Card';

const LinkTable = ({ links, onDelete, onToggle, onRefresh }) => {
    const [copyingId, setCopyingId] = useState(null);
    const [deletingId, setDeletingId] = useState(null);
    const [togglingId, setTogglingId] = useState(null);

    const handleCopy = async (url, id) => {
        try {
            await navigator.clipboard.writeText(url);
            setCopyingId(id);
            setTimeout(() => setCopyingId(null), 2000);
        } catch (error) {
            console.error('Failed to copy:', error);
        }
    };

    const handleDelete = async (id) => {
        if (window.confirm('Are you sure you want to delete this link? This action cannot be undone.')) {
            setDeletingId(id);
            try {
                await onDelete(id);
                onRefresh();
            } catch (error) {
                console.error('Delete failed:', error);
            } finally {
                setDeletingId(null);
            }
        }
    };

    const handleToggle = async (id) => {
        setTogglingId(id);
        try {
            await onToggle(id);
            onRefresh();
        } catch (error) {
            console.error('Toggle failed:', error);
        } finally {
            setTogglingId(null);
        }
    };

    if (links.length === 0) {
        return (
            <Card className="text-center py-12">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
                        <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                        </svg>
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-1">No links yet</h3>
                        <p className="text-gray-600 mb-4">Create your first short link to get started</p>
                        <Button variant="primary" onClick={() => window.location.href = '/create'}>
                            Create Link
                        </Button>
                    </div>
                </div>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            {/* Desktop Table */}
            <div className="hidden lg:block">
                <Card padding={false} className="overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Original URL
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Short Link
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Clicks
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Status
                                    </th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {links.map((link) => (
                                    <tr key={link.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="max-w-xs">
                                                <a
                                                    href={link.original_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-sm text-primary-600 hover:text-primary-800 truncate block"
                                                    title={link.original_url}
                                                >
                                                    {link.original_url}
                                                </a>
                                                {link.title && (
                                                    <p className="text-xs text-gray-500 mt-1">{link.title}</p>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <code className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                                                    {link.short_url}
                                                </code>
                                                <button
                                                    onClick={() => handleCopy(link.short_url, link.id)}
                                                    className="text-gray-400 hover:text-gray-600 transition-colors"
                                                    title="Copy to clipboard"
                                                >
                                                    {copyingId === link.id ? (
                                                        <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    ) : (
                                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                                        </svg>
                                                    )}
                                                </button>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                                </svg>
                                                <span className="text-sm font-medium text-gray-900">{link.clicks}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            {link.is_active && !link.is_expired ? (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                    Active
                                                </span>
                                            ) : link.is_expired ? (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                                    Expired
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                                    Inactive
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => handleToggle(link.id)}
                                                    disabled={togglingId === link.id || link.is_expired}
                                                    className="text-sm text-primary-600 hover:text-primary-800 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                                                >
                                                    {togglingId === link.id ? 'Loading...' : link.is_active ? 'Disable' : 'Enable'}
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(link.id)}
                                                    disabled={deletingId === link.id}
                                                    className="text-sm text-red-600 hover:text-red-800 font-medium disabled:opacity-50"
                                                >
                                                    {deletingId === link.id ? 'Deleting...' : 'Delete'}
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </div>

            {/* Mobile Cards */}
            <div className="lg:hidden space-y-4">
                {links.map((link) => (
                    <Card key={link.id} className="space-y-3">
                        <div>
                            <a
                                href={link.original_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-primary-600 hover:text-primary-800 break-all"
                            >
                                {link.original_url}
                            </a>
                            {link.title && (
                                <p className="text-xs text-gray-500 mt-1">{link.title}</p>
                            )}
                        </div>

                        <div className="flex items-center justify-between gap-2 bg-gray-50 px-3 py-2 rounded-lg">
                            <code className="text-xs font-mono text-gray-700 truncate">
                                {link.short_url}
                            </code>
                            <button
                                onClick={() => handleCopy(link.short_url, link.id)}
                                className="text-gray-400 hover:text-gray-600 flex-shrink-0"
                            >
                                {copyingId === link.id ? (
                                    <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                ) : (
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                    </svg>
                                )}
                            </button>
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="flex items-center gap-1 text-sm text-gray-600">
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                    </svg>
                                    <span className="font-medium">{link.clicks}</span>
                                </div>

                                {link.is_active && !link.is_expired ? (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        Active
                                    </span>
                                ) : link.is_expired ? (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        Expired
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                        Inactive
                                    </span>
                                )}
                            </div>

                            <div className="flex items-center gap-2">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleToggle(link.id)}
                                    disabled={togglingId === link.id || link.is_expired}
                                >
                                    {togglingId === link.id ? '...' : link.is_active ? 'Disable' : 'Enable'}
                                </Button>
                                <Button
                                    variant="danger"
                                    size="sm"
                                    onClick={() => handleDelete(link.id)}
                                    disabled={deletingId === link.id}
                                >
                                    {deletingId === link.id ? '...' : 'Delete'}
                                </Button>
                            </div>
                        </div>
                    </Card>
                ))}
            </div>
        </div>
    );
};

export default LinkTable;