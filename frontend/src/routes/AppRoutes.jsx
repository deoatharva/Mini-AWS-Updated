import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { AuthProvider } from '../auth/AuthContext.jsx';
import {
  ProtectedRoute,
  PublicOnlyRoute,
  RequirePermission,
} from '../components/RouteGuards.jsx';
import { ConsoleLayout } from '../layouts/ConsoleLayout.jsx';
import Account from '../pages/Account.jsx';
import Dashboard from '../pages/Dashboard.jsx';
import IAMAudit from '../pages/iam/IAMAudit.jsx';
import IAMGroupCreate from '../pages/iam/IAMGroupCreate.jsx';
import IAMGroupDetail from '../pages/iam/IAMGroupDetail.jsx';
import IAMGroups from '../pages/iam/IAMGroups.jsx';
import IAMOverview from '../pages/iam/IAMOverview.jsx';
import IAMPolicyCreate from '../pages/iam/IAMPolicyCreate.jsx';
import IAMPolicyDetail from '../pages/iam/IAMPolicyDetail.jsx';
import IAMPolicies from '../pages/iam/IAMPolicies.jsx';
import IAMUserCreate from '../pages/iam/IAMUserCreate.jsx';
import IAMUserDetail from '../pages/iam/IAMUserDetail.jsx';
import IAMUsers from '../pages/iam/IAMUsers.jsx';
import IAMLogin from '../pages/IAMLogin.jsx';
import MandatoryPasswordChange from '../pages/MandatoryPasswordChange.jsx';
import Databases from '../pages/databases/Databases.jsx';
import Instances from '../pages/compute/Instances.jsx';
import Applications from '../pages/deployment/Applications.jsx';
import Login from '../pages/Login.jsx';
import NotFound from '../pages/NotFound.jsx';
import Register from '../pages/Register.jsx';
import Buckets from '../pages/storage/Buckets.jsx';

function Allowed({ action, children }) {
  return <RequirePermission action={action}>{children}</RequirePermission>;
}

export function AppRoutes() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<PublicOnlyRoute />}>
            <Route path="/login" element={<Login />} />
            <Route path="/login/iam" element={<IAMLogin />} />
            <Route path="/register" element={<Register />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route
              path="/account/change-password"
              element={<MandatoryPasswordChange />}
            />
            <Route path="/" element={<ConsoleLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="compute/instances" element={<Instances />} />
              <Route path="applications" element={<Applications />} />
              <Route path="storage/buckets" element={<Buckets />} />
              <Route path="databases" element={<Databases />} />
              <Route path="account" element={<Account />} />

              <Route
                path="iam"
                element={
                  <Allowed action="iam:ReadOverview">
                    <IAMOverview />
                  </Allowed>
                }
              />
              <Route
                path="iam/users"
                element={
                  <Allowed action="iam:ListUsers">
                    <IAMUsers />
                  </Allowed>
                }
              />
              <Route
                path="iam/users/new"
                element={
                  <Allowed action="iam:CreateUser">
                    <IAMUserCreate />
                  </Allowed>
                }
              />
              <Route
                path="iam/users/:userId"
                element={
                  <Allowed action="iam:GetUser">
                    <IAMUserDetail />
                  </Allowed>
                }
              />
              <Route
                path="iam/groups"
                element={
                  <Allowed action="iam:ListGroups">
                    <IAMGroups />
                  </Allowed>
                }
              />
              <Route
                path="iam/groups/new"
                element={
                  <Allowed action="iam:CreateGroup">
                    <IAMGroupCreate />
                  </Allowed>
                }
              />
              <Route
                path="iam/groups/:groupId"
                element={
                  <Allowed action="iam:GetGroup">
                    <IAMGroupDetail />
                  </Allowed>
                }
              />
              <Route
                path="iam/policies"
                element={
                  <Allowed action="iam:ListPolicies">
                    <IAMPolicies />
                  </Allowed>
                }
              />
              <Route
                path="iam/policies/new"
                element={
                  <Allowed action="iam:CreatePolicy">
                    <IAMPolicyCreate />
                  </Allowed>
                }
              />
              <Route
                path="iam/policies/:policyId"
                element={
                  <Allowed action="iam:GetPolicy">
                    <IAMPolicyDetail />
                  </Allowed>
                }
              />
              <Route
                path="iam/audit"
                element={
                  <Allowed action="iam:ListAuditLogs">
                    <IAMAudit />
                  </Allowed>
                }
              />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
