import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { AuthProvider } from '../auth/AuthContext.jsx';
import { ProtectedRoute, PublicOnlyRoute } from '../components/RouteGuards.jsx';
import { ConsoleLayout } from '../layouts/ConsoleLayout.jsx';
import Account from '../pages/Account.jsx';
import Dashboard from '../pages/Dashboard.jsx';
import Databases from '../pages/databases/Databases.jsx';
import Instances from '../pages/compute/Instances.jsx';
import Applications from '../pages/deployment/Applications.jsx';
import Login from '../pages/Login.jsx';
import NotFound from '../pages/NotFound.jsx';
import Register from '../pages/Register.jsx';
import Buckets from '../pages/storage/Buckets.jsx';

export function AppRoutes() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<PublicOnlyRoute />}>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<ConsoleLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="compute/instances" element={<Instances />} />
              <Route path="applications" element={<Applications />} />
              <Route path="storage/buckets" element={<Buckets />} />
              <Route path="databases" element={<Databases />} />
              <Route path="account" element={<Account />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
