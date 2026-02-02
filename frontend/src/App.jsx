import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import ProtectedRoute from './auth/ProtectedRoute';
import Navbar from './components/Navbar';
import Footer from './components/Footer';

// Pages
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './pages/Dashboard';
import CreateLink from './pages/CreateLink';
import NotFound from './pages/NotFound';
import RedirectHandler from './pages/RedirectHandler';

// App routes
const APP_ROUTES = [
  'login',
  'register',
  'dashboard',
  'create',
  'forgot-password',
  'reset-password',
  '404',
  'favicon.ico',
  'robots.txt',
  'sitemap.xml'
];

// Smart redirect component
const SmartRedirect = () => {
  const { slug } = useParams();

  // Check if it's an app route or static file
  if (!slug || APP_ROUTES.includes(slug.toLowerCase())) {
    return <Navigate to="/404" replace />;
  }

  // Check if slug starts with common static paths
  if (slug.startsWith('_next') || slug.startsWith('static') || slug.startsWith('assets')) {
    return <Navigate to="/404" replace />;
  }

  return <RedirectHandler />;
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="flex flex-col min-h-screen">
          <Navbar />
          <main className="flex-grow">
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />

              {/* Protected Routes */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/create"
                element={
                  <ProtectedRoute>
                    <CreateLink />
                  </ProtectedRoute>
                }
              />

              {/* 404 Page */}
              <Route path="/404" element={<NotFound />} />

              {/* Short Link Redirect Handler - Must be LAST before catch-all */}
              <Route path="/:slug" element={<SmartRedirect />} />

              {/* Fallback to 404 */}
              <Route path="*" element={<Navigate to="/404" replace />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;