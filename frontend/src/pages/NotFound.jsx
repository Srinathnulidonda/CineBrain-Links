import { Link } from 'react-router-dom';
import Button from '../components/Button';

const NotFound = () => {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50 px-4">
            <div className="text-center">
                <div className="mb-8">
                    <h1 className="text-9xl font-extrabold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                        404
                    </h1>
                    <div className="text-6xl mb-4">🔍</div>
                    <h2 className="text-3xl font-bold text-gray-900 mb-2">Page not found</h2>
                    <p className="text-gray-600 mb-8 max-w-md">
                        Sorry, we couldn't find the page you're looking for. It might have been moved or deleted.
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <Link to="/">
                        <Button variant="primary" size="lg">
                            Go Home
                        </Button>
                    </Link>
                    <Link to="/dashboard">
                        <Button variant="outline" size="lg">
                            Dashboard
                        </Button>
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default NotFound;