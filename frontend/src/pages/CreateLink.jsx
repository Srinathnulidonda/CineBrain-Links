import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import Input from '../components/Input';
import Button from '../components/Button';
import Card from '../components/Card';

const CreateLink = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        url: '',
        custom_slug: '',
        expires_at: '',
        title: '',
        description: ''
    });
    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);
    const [checkingSlug, setCheckingSlug] = useState(false);
    const [slugAvailable, setSlugAvailable] = useState(null);
    const [createdLink, setCreatedLink] = useState(null);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));

        if (errors[name]) {
            setErrors(prev => ({ ...prev, [name]: '' }));
        }

        // Check slug availability on change
        if (name === 'custom_slug' && value.length >= 4) {
            checkSlugAvailability(value);
        } else if (name === 'custom_slug') {
            setSlugAvailable(null);
        }
    };

    const checkSlugAvailability = async (slug) => {
        setCheckingSlug(true);
        try {
            const response = await api.links.checkSlug(slug);
            setSlugAvailable(response.data.available);
        } catch (error) {
            setSlugAvailable(null);
        } finally {
            setCheckingSlug(false);
        }
    };

    const validate = () => {
        const newErrors = {};

        // URL validation
        if (!formData.url) {
            newErrors.url = 'URL is required';
        } else if (!/^https?:\/\/.+/.test(formData.url)) {
            newErrors.url = 'URL must start with http:// or https://';
        }

        // Custom slug validation (optional)
        if (formData.custom_slug) {
            if (formData.custom_slug.length < 4) {
                newErrors.custom_slug = 'Slug must be at least 4 characters';
            } else if (formData.custom_slug.length > 20) {
                newErrors.custom_slug = 'Slug must not exceed 20 characters';
            } else if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$/.test(formData.custom_slug)) {
                newErrors.custom_slug = 'Slug can only contain letters, numbers, hyphens, and underscores';
            } else if (slugAvailable === false) {
                newErrors.custom_slug = 'This slug is already taken';
            }
        }

        // Expiration date validation (optional)
        if (formData.expires_at) {
            const expiryDate = new Date(formData.expires_at);
            const now = new Date();
            if (expiryDate <= now) {
                newErrors.expires_at = 'Expiration date must be in the future';
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validate()) return;

        setLoading(true);

        try {
            const payload = {
                url: formData.url,
                ...(formData.custom_slug && { custom_slug: formData.custom_slug }),
                ...(formData.expires_at && { expires_at: new Date(formData.expires_at).toISOString() }),
                ...(formData.title && { title: formData.title }),
                ...(formData.description && { description: formData.description })
            };

            const response = await api.links.create(payload);
            setCreatedLink(response.data.link);
        } catch (error) {
            const message = error.response?.data?.error || 'Failed to create link. Please try again.';
            setErrors({ api: message });
        } finally {
            setLoading(false);
        }
    };

    const handleCopy = async (url) => {
        try {
            await navigator.clipboard.writeText(url);
        } catch (error) {
            console.error('Failed to copy:', error);
        }
    };

    if (createdLink) {
        return (
            <div className="min-h-screen bg-gray-50 py-8">
                <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
                    <Card className="text-center animate-slide-up">
                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                        </div>

                        <h2 className="text-2xl font-bold text-gray-900 mb-2">Link Created Successfully!</h2>
                        <p className="text-gray-600 mb-6">Your short link is ready to use</p>

                        <div className="bg-gray-50 rounded-lg p-6 mb-6">
                            <p className="text-sm text-gray-600 mb-2">Your short link:</p>
                            <div className="flex items-center justify-center gap-3 mb-4">
                                <code className="text-lg font-mono bg-white px-4 py-2 rounded border border-gray-200">
                                    {createdLink.short_url}
                                </code>
                                <button
                                    onClick={() => handleCopy(createdLink.short_url)}
                                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
                                    title="Copy to clipboard"
                                >
                                    <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                    </svg>
                                </button>
                            </div>

                            <div className="text-left bg-white rounded border border-gray-200 p-4">
                                <div className="text-sm text-gray-600 mb-1">Original URL:</div>
                                <a
                                    href={createdLink.original_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-primary-600 hover:text-primary-700 break-all"
                                >
                                    {createdLink.original_url}
                                </a>
                            </div>
                        </div>

                        <div className="flex flex-col sm:flex-row gap-3 justify-center">
                            <Button variant="primary" onClick={() => navigate('/dashboard')}>
                                Go to Dashboard
                            </Button>
                            <Button variant="outline" onClick={() => {
                                setCreatedLink(null);
                                setFormData({
                                    url: '',
                                    custom_slug: '',
                                    expires_at: '',
                                    title: '',
                                    description: ''
                                });
                            }}>
                                Create Another Link
                            </Button>
                        </div>
                    </Card>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Create Short Link</h1>
                    <p className="text-gray-600">Shorten your URL and make it memorable</p>
                </div>

                <Card>
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {errors.api && (
                            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                                <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                <p className="text-sm text-red-800">{errors.api}</p>
                            </div>
                        )}

                        <Input
                            label="Destination URL"
                            type="url"
                            name="url"
                            value={formData.url}
                            onChange={handleChange}
                            placeholder="https://example.com/your-long-url"
                            error={errors.url}
                            required
                            helperText="The URL you want to shorten"
                            icon={
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                                </svg>
                            }
                        />

                        <div>
                            <Input
                                label="Custom Slug (Optional)"
                                type="text"
                                name="custom_slug"
                                value={formData.custom_slug}
                                onChange={handleChange}
                                placeholder="my-custom-link"
                                error={errors.custom_slug}
                                helperText="Leave empty to auto-generate"
                            />
                            {checkingSlug && (
                                <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                                    <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Checking availability...
                                </p>
                            )}
                            {!checkingSlug && slugAvailable === true && formData.custom_slug && (
                                <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                    </svg>
                                    This slug is available!
                                </p>
                            )}
                        </div>

                        <Input
                            label="Title (Optional)"
                            type="text"
                            name="title"
                            value={formData.title}
                            onChange={handleChange}
                            placeholder="My Campaign Link"
                            helperText="Help you identify this link later"
                        />

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                Description (Optional)
                            </label>
                            <textarea
                                name="description"
                                value={formData.description}
                                onChange={handleChange}
                                placeholder="Add notes about this link..."
                                rows={3}
                                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-opacity-50 focus:outline-none transition-all duration-200"
                            />
                        </div>

                        <Input
                            label="Expiration Date (Optional)"
                            type="datetime-local"
                            name="expires_at"
                            value={formData.expires_at}
                            onChange={handleChange}
                            error={errors.expires_at}
                            helperText="Link will stop working after this date"
                        />

                        <div className="flex gap-3 pt-4">
                            <Button
                                type="submit"
                                variant="primary"
                                fullWidth
                                loading={loading}
                                disabled={loading || checkingSlug || (formData.custom_slug && slugAvailable === false)}
                            >
                                Create Short Link
                            </Button>
                            <Button
                                type="button"
                                variant="ghost"
                                onClick={() => navigate('/dashboard')}
                            >
                                Cancel
                            </Button>
                        </div>
                    </form>
                </Card>
            </div>
        </div>
    );
};

export default CreateLink;