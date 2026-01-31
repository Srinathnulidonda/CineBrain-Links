import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import Input from '../components/Input';
import Button from '../components/Button';
import Card from '../components/Card';

const ForgotPassword = () => {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (!email) {
            setError('Email is required');
            return;
        }

        if (!/\S+@\S+\.\S+/.test(email)) {
            setError('Please enter a valid email address');
            return;
        }

        setLoading(true);

        try {
            await api.auth.forgotPassword(email);
            setSubmitted(true);
        } catch (error) {
            // Always show success message to prevent email enumeration
            setSubmitted(true);
        } finally {
            setLoading(false);
        }
    };

    if (submitted) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50 px-4 py-12">
                <div className="w-full max-w-md animate-slide-up">
                    <Card className="text-center">
                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900 mb-2">Check your email</h2>
                        <p className="text-gray-600 mb-6">
                            If an account exists with <strong>{email}</strong>, you will receive a password reset link shortly.
                        </p>
                        <p className="text-sm text-gray-500 mb-6">
                            The link will expire in 1 hour for security reasons.
                        </p>
                        <Link to="/login">
                            <Button variant="primary" fullWidth>
                                Back to Login
                            </Button>
                        </Link>
                    </Card>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50 px-4 py-12">
            <div className="w-full max-w-md animate-slide-up">
                <div className="text-center mb-8">
                    <Link to="/" className="inline-flex items-center gap-2 mb-6 group">
                        <div className="w-12 h-12 bg-gradient-to-br from-primary-600 to-secondary-600 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform">
                            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                            </svg>
                        </div>
                        <span className="text-2xl font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                            CinBrainLinks
                        </span>
                    </Link>
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Forgot password?</h1>
                    <p className="text-gray-600">Enter your email and we'll send you a reset link</p>
                </div>

                <Card>
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <Input
                            label="Email"
                            type="email"
                            name="email"
                            value={email}
                            onChange={(e) => {
                                setEmail(e.target.value);
                                setError('');
                            }}
                            placeholder="you@example.com"
                            error={error}
                            required
                            icon={
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                                </svg>
                            }
                        />

                        <Button
                            type="submit"
                            variant="primary"
                            fullWidth
                            loading={loading}
                            disabled={loading}
                        >
                            Send Reset Link
                        </Button>
                    </form>

                    <div className="mt-6 text-center">
                        <Link to="/login" className="text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors">
                            ← Back to login
                        </Link>
                    </div>
                </Card>
            </div>
        </div>
    );
};

export default ForgotPassword;