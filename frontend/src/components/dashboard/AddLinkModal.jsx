// src/components/dashboard/AddLinkModal.jsx
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export default function AddLinkModal({ isOpen, onClose, onSubmit }) {
    const [formData, setFormData] = useState({
        original_url: '',
        title: '',
        notes: '',
        link_type: 'saved',
        tags: [],
        collection_id: null,
    });
    const [currentTag, setCurrentTag] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [duplicateWarning, setDuplicateWarning] = useState(null);

    useEffect(() => {
        // Reset form when modal opens
        if (isOpen) {
            setFormData({
                original_url: '',
                title: '',
                notes: '',
                link_type: 'saved',
                tags: [],
                collection_id: null,
            });
            setError('');
            setDuplicateWarning(null);
        }
    }, [isOpen]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!formData.original_url) {
            setError('URL is required');
            return;
        }

        setLoading(true);
        try {
            await onSubmit(formData);
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to save link');
        } finally {
            setLoading(false);
        }
    };

    const handlePaste = async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text && text.startsWith('http')) {
                setFormData({ ...formData, original_url: text });
                // Auto-fetch title if possible
                fetchTitleFromUrl(text);
            }
        } catch (err) {
            console.error('Failed to read clipboard');
        }
    };

    const fetchTitleFromUrl = async (url) => {
        // This would typically call an API to fetch the page title
        // For now, we'll just extract the domain
        try {
            const urlObj = new URL(url);
            const domain = urlObj.hostname.replace('www.', '');
            setFormData(prev => ({
                ...prev,
                title: prev.title || domain
            }));
        } catch (err) {
            console.error('Invalid URL');
        }
    };

    const handleAddTag = (e) => {
        if (e.key === 'Enter' && currentTag.trim()) {
            e.preventDefault();
            if (!formData.tags.includes(currentTag.trim())) {
                setFormData({
                    ...formData,
                    tags: [...formData.tags, currentTag.trim()]
                });
            }
            setCurrentTag('');
        }
    };

    const removeTag = (tagToRemove) => {
        setFormData({
            ...formData,
            tags: formData.tags.filter(tag => tag !== tagToRemove)
        });
    };

    if (!isOpen) return null;

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                className="w-full max-w-2xl rounded-xl border border-gray-800 bg-gray-950 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between border-b border-gray-800 p-4 sm:p-6">
                    <h2 className="text-lg sm:text-xl font-semibold text-white">
                        Add New Link
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white transition-colors"
                    >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-4 sm:p-6">
                    {/* Link Type Toggle */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                            What do you want to do?
                        </label>
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={() => setFormData({ ...formData, link_type: 'saved' })}
                                className={`flex-1 rounded-lg px-4 py-3 text-sm font-medium transition-all ${formData.link_type === 'saved'
                                        ? 'bg-primary text-white'
                                        : 'border border-gray-800 text-gray-400 hover:bg-gray-900 hover:text-white'
                                    }`}
                            >
                                <svg className="inline h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                                </svg>
                                Save for Later
                            </button>
                            <button
                                type="button"
                                onClick={() => setFormData({ ...formData, link_type: 'shortened' })}
                                className={`flex-1 rounded-lg px-4 py-3 text-sm font-medium transition-all ${formData.link_type === 'shortened'
                                        ? 'bg-primary text-white'
                                        : 'border border-gray-800 text-gray-400 hover:bg-gray-900 hover:text-white'
                                    }`}
                            >
                                <svg className="inline h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
                                </svg>
                                Create Short Link
                            </button>
                        </div>
                    </div>

                    {/* URL Input */}
                    <div className="mb-4">
                        <label htmlFor="url" className="block text-sm font-medium text-gray-300 mb-2">
                            URL <span className="text-red-400">*</span>
                        </label>
                        <div className="flex gap-2">
                            <input
                                id="url"
                                type="url"
                                value={formData.original_url}
                                onChange={(e) => setFormData({ ...formData, original_url: e.target.value })}
                                className="flex-1 rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                                placeholder="https://example.com"
                                required
                            />
                            <button
                                type="button"
                                onClick={handlePaste}
                                className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-all"
                            >
                                Paste
                            </button>
                        </div>
                        {error && (
                            <p className="mt-2 text-sm text-red-400">{error}</p>
                        )}
                    </div>

                    {/* Title Input */}
                    <div className="mb-4">
                        <label htmlFor="title" className="block text-sm font-medium text-gray-300 mb-2">
                            Title
                        </label>
                        <input
                            id="title"
                            type="text"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            className="w-full rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                            placeholder="Enter a title (optional)"
                        />
                    </div>

                    {/* Notes */}
                    <div className="mb-4">
                        <label htmlFor="notes" className="block text-sm font-medium text-gray-300 mb-2">
                            Notes
                        </label>
                        <textarea
                            id="notes"
                            value={formData.notes}
                            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                            rows={3}
                            className="w-full rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                            placeholder="Add notes or description..."
                        />
                    </div>

                    {/* Tags */}
                    <div className="mb-6">
                        <label htmlFor="tags" className="block text-sm font-medium text-gray-300 mb-2">
                            Tags
                        </label>
                        <div className="flex flex-wrap gap-2 mb-2">
                            {formData.tags.map((tag) => (
                                <span
                                    key={tag}
                                    className="inline-flex items-center gap-1 rounded-full bg-gray-800 px-3 py-1 text-xs text-gray-300"
                                >
                                    {tag}
                                    <button
                                        type="button"
                                        onClick={() => removeTag(tag)}
                                        className="text-gray-500 hover:text-white"
                                    >
                                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </span>
                            ))}
                        </div>
                        <input
                            id="tags"
                            type="text"
                            value={currentTag}
                            onChange={(e) => setCurrentTag(e.target.value)}
                            onKeyDown={handleAddTag}
                            className="w-full rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                            placeholder="Type and press Enter to add tags"
                        />
                    </div>

                    {/* Duplicate Warning */}
                    {duplicateWarning && (
                        <div className="mb-6 rounded-lg bg-yellow-500/10 border border-yellow-500/20 p-4">
                            <p className="text-sm text-yellow-400">
                                ⚠️ You already saved this URL: "{duplicateWarning.existing_title}"
                            </p>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 rounded-lg border border-gray-800 bg-gray-900 px-4 py-2.5 text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading || !formData.original_url}
                            className="flex-1 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                            {loading ? 'Saving...' : formData.link_type === 'shortened' ? 'Create Short Link' : 'Save Link'}
                        </button>
                    </div>
                </form>
            </motion.div>
        </motion.div>
    );
}