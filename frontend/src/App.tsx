import { Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { ThemeProvider } from '@/components/theme-provider'
import { AuthProvider } from '@/hooks/use-auth'
import { ProtectedRoute } from '@/components/auth/protected-route'

// Pages
import HomePage from '@/pages/home'
import LoginPage from '@/pages/auth/login'
import RegisterPage from '@/pages/auth/register'
import DashboardPage from '@/pages/dashboard'
import BusinessesPage from '@/pages/businesses'
import BusinessDetailPage from '@/pages/businesses/[id]'
import ReportsPage from '@/pages/reports'
import AdminPage from '@/pages/admin'
import PricingPage from '@/pages/pricing'
import FeaturesPage from '@/pages/features'
import AboutPage from '@/pages/about'
import ContactPage from '@/pages/contact'
import FAQPage from '@/pages/faq'
import NotFoundPage from '@/pages/404'

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="central-florida-seo-theme">
      <AuthProvider>
        <div className="min-h-screen bg-background">
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<HomePage />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/features" element={<FeaturesPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/faq" element={<FAQPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            
            {/* Protected routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } />
            <Route path="/businesses" element={
              <ProtectedRoute>
                <BusinessesPage />
              </ProtectedRoute>
            } />
            <Route path="/businesses/:id" element={
              <ProtectedRoute>
                <BusinessDetailPage />
              </ProtectedRoute>
            } />
            <Route path="/reports" element={
              <ProtectedRoute>
                <ReportsPage />
              </ProtectedRoute>
            } />
            
            {/* Admin routes */}
            <Route path="/admin" element={
              <ProtectedRoute requireAdmin>
                <AdminPage />
              </ProtectedRoute>
            } />
            
            {/* 404 */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
          
          <Toaster />
        </div>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App