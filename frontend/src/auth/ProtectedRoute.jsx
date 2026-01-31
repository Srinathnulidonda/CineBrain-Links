import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import Loader from '../components/Loader';

const ProtectedRoute = ({ children }) => {
    const { isAuthenticated, loading, initialized } = useAuth();
    const location = useLocation();

    // Wait for auth to initialize
    if (!initialized || loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader />
            </div>
        );
    }

    if (!isAuthenticated) {
        // Redirect to login, save attempted location
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return children;
};

export default ProtectedRoute;