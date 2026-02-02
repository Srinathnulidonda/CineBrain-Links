import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import Loader from '../components/Loader';

const RedirectHandler = () => {
    const { slug } = useParams();

    // Your Render backend URL
    const BACKEND_URL = import.meta.env.VITE_API_BASE_URL || 'https://cinebrainlinks.onrender.com';

    useEffect(() => {
        if (slug) {
            // Redirect to backend which handles the actual redirect + click counting
            window.location.href = `${BACKEND_URL}/${slug}`;
        }
    }, [slug, BACKEND_URL]);

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50">
            <Loader size="lg" />
            <p className="mt-4 text-gray-600 text-lg">Redirecting you...</p>
            <p className="mt-2 text-gray-400 text-sm">Please wait a moment</p>
        </div>
    );
};

export default RedirectHandler;