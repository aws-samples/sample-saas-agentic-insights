import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import TenantManagement from './pages/TenantManagement';
import CostAnalysis from './pages/CostAnalysis';
import UsageAnalysis from './pages/UsageAnalysis';
import ChurnAnalysis from './pages/ChurnAnalysis';

function App() {
  const isAuthenticated = () => {
    const token = localStorage.getItem('adminToken');
    return token && !isTokenExpired(token);
  };

  const isTokenExpired = (token: string) => {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return Date.now() >= payload.exp * 1000;
    } catch {
      return true;
    }
  };

  const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
    return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />;
  };

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }>
          <Route index element={<Navigate to="/tenants" replace />} />
          <Route path="tenants" element={<TenantManagement />} />
          <Route path="cost-analysis" element={<CostAnalysis />} />
          <Route path="usage-analysis" element={<UsageAnalysis />} />
          <Route path="churn-analysis" element={<ChurnAnalysis />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
