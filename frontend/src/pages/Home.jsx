import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import Button from '../components/Button';
import Card from '../components/Card';

const Home = () => {
    const { isAuthenticated } = useAuth();

    return (
        <div className="min-h-screen">
            {/* Hero Section */}
            <section className="relative overflow-hidden bg-gradient-to-br from-primary-50 via-white to-secondary-50">
                <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>

                <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28">
                    <div className="text-center max-w-4xl mx-auto">
                        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold text-gray-900 mb-6 leading-tight">
                            Create{' '}
                            <span className="bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                                branded links
                            </span>
                            {' '}that build trust
                        </h1>

                        <p className="text-xl sm:text-2xl text-gray-600 mb-10 leading-relaxed max-w-3xl mx-auto">
                            CinBrainLinks helps you create memorable short links, track engagement, and strengthen your brand presence online.
                        </p>

                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            {isAuthenticated ? (
                                <Link to="/dashboard">
                                    <Button variant="primary" size="lg" className="min-w-[200px]">
                                        Go to Dashboard
                                    </Button>
                                </Link>
                            ) : (
                                <>
                                    <Link to="/register">
                                        <Button variant="primary" size="lg" className="min-w-[200px]">
                                            Get Started Free
                                        </Button>
                                    </Link>
                                    <Link to="/login">
                                        <Button variant="outline" size="lg" className="min-w-[200px]">
                                            Sign In
                                        </Button>
                                    </Link>
                                </>
                            )}
                        </div>

                        <p className="mt-6 text-sm text-gray-500">
                            No credit card required • Free forever plan
                        </p>
                    </div>

                    {/* Preview Image */}
                    <div className="mt-16 relative">
                        <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent z-10"></div>
                        <Card className="max-w-4xl mx-auto shadow-2xl">
                            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-8 border border-gray-200">
                                <div className="space-y-3">
                                    <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                                    <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                                    <div className="mt-6 grid grid-cols-3 gap-4">
                                        <div className="h-24 bg-gradient-to-br from-primary-100 to-primary-200 rounded-lg"></div>
                                        <div className="h-24 bg-gradient-to-br from-secondary-100 to-secondary-200 rounded-lg"></div>
                                        <div className="h-24 bg-gradient-to-br from-purple-100 to-purple-200 rounded-lg"></div>
                                    </div>
                                </div>
                            </div>
                        </Card>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold text-gray-900 mb-4">
                            Everything you need to manage your links
                        </h2>
                        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                            Powerful features designed for teams and individuals who care about their brand
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8">
                        <Card hover className="text-center">
                            <div className="w-14 h-14 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Custom Slugs</h3>
                            <p className="text-gray-600">
                                Create memorable branded links with custom slugs that reflect your brand identity
                            </p>
                        </Card>

                        <Card hover className="text-center">
                            <div className="w-14 h-14 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Real-time Analytics</h3>
                            <p className="text-gray-600">
                                Track clicks and engagement with powerful analytics to understand your audience
                            </p>
                        </Card>

                        <Card hover className="text-center">
                            <div className="w-14 h-14 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Secure & Reliable</h3>
                            <p className="text-gray-600">
                                Enterprise-grade security with 99.9% uptime. Your links are always available
                            </p>
                        </Card>

                        <Card hover className="text-center">
                            <div className="w-14 h-14 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Link Expiration</h3>
                            <p className="text-gray-600">
                                Set expiration dates for time-sensitive campaigns and promotions
                            </p>
                        </Card>

                        <Card hover className="text-center">
                            <div className="w-14 h-14 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Link Management</h3>
                            <p className="text-gray-600">
                                Easily enable, disable, or delete links with our intuitive dashboard
                            </p>
                        </Card>

                        <Card hover className="text-center">
                            <div className="w-14 h-14 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Lightning Fast</h3>
                            <p className="text-gray-600">
                                Redirects happen in milliseconds with our globally distributed infrastructure
                            </p>
                        </Card>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 bg-gradient-to-br from-primary-600 to-secondary-600">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                    <h2 className="text-4xl font-bold text-white mb-6">
                        Ready to get started?
                    </h2>
                    <p className="text-xl text-primary-100 mb-10">
                        Join thousands of users who trust CinBrainLinks for their branded short links
                    </p>
                    {!isAuthenticated && (
                        <Link to="/register">
                            <Button variant="secondary" size="lg" className="bg-white text-primary-700 hover:bg-gray-100 min-w-[200px]">
                                Create Free Account
                            </Button>
                        </Link>
                    )}
                </div>
            </section>
        </div>
    );
};

export default Home;