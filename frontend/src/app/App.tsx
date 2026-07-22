import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../lib/auth";

const Applicants = lazy(() => import("../pages/Applicants"));
const ApplicantDetail = lazy(() => import("../pages/ApplicantDetail"));
const AuditLog = lazy(() => import("../pages/AuditLog"));
const Home = lazy(() => import("../pages/Home"));
const LoanDetail = lazy(() => import("../pages/LoanDetail"));
const Loans = lazy(() => import("../pages/Loans"));
const Login = lazy(() => import("../pages/Login"));
const NewApplicant = lazy(() => import("../pages/NewApplicant"));
const NewLoan = lazy(() => import("../pages/NewLoan"));
const Notifications = lazy(() => import("../pages/Notifications"));
const Reports = lazy(() => import("../pages/Reports"));
const Security = lazy(() => import("../pages/Security"));
const Users = lazy(() => import("../pages/Users"));
const Integrations = lazy(() => import("../pages/Integrations"));
const Organization = lazy(() => import("../pages/Organization"));
const FraudAlerts = lazy(() => import("../pages/FraudAlerts"));
const LoanProducts = lazy(() => import("../pages/LoanProducts"));
const Roles = lazy(() => import("../pages/Roles"));
const ModelOperations = lazy(() => import("../pages/ModelOperations"));
const TenantManagement = lazy(() => import("../pages/TenantManagement"));

function LoadingScreen() {
  return <div className="grid min-h-screen place-items-center text-slate-500">Loading…</div>;
}

function Protected({ children }: { children: React.ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!me) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function Authorized({ permission, children }: { permission: string; children: React.ReactNode }) {
  const { can } = useAuth();
  return can(permission) ? children : <Navigate to="/notifications" replace />;
}

export default function App() {
  return (
    <Suspense fallback={<LoadingScreen />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Protected><Home /></Protected>} />
        <Route path="/loans" element={<Protected><Authorized permission="loan:read"><Loans /></Authorized></Protected>} />
        <Route path="/loans/new" element={<Protected><Authorized permission="loan:create"><NewLoan /></Authorized></Protected>} />
        <Route path="/loans/:id" element={<Protected><Authorized permission="loan:read"><LoanDetail /></Authorized></Protected>} />
        <Route path="/applicants" element={<Protected><Authorized permission="applicant:read"><Applicants /></Authorized></Protected>} />
        <Route path="/applicants/:id" element={<Protected><Authorized permission="applicant:read"><ApplicantDetail /></Authorized></Protected>} />
        <Route path="/applicants/new" element={<Protected><Authorized permission="applicant:manage"><NewApplicant /></Authorized></Protected>} />
        <Route path="/reports" element={<Protected><Authorized permission="report:export"><Reports /></Authorized></Protected>} />
        <Route path="/notifications" element={<Protected><Notifications /></Protected>} />
        <Route path="/security" element={<Protected><Security /></Protected>} />
        <Route path="/users" element={<Protected><Authorized permission="user:manage"><Users /></Authorized></Protected>} />
        <Route path="/integrations" element={<Protected><Authorized permission="org:configure"><Integrations /></Authorized></Protected>} />
        <Route path="/organization" element={<Protected><Authorized permission="org:configure"><Organization /></Authorized></Protected>} />
        <Route path="/fraud" element={<Protected><Authorized permission="fraud:read"><FraudAlerts /></Authorized></Protected>} />
        <Route path="/loan-products" element={<Protected><Authorized permission="org:configure"><LoanProducts /></Authorized></Protected>} />
        <Route path="/roles" element={<Protected><Authorized permission="role:manage"><Roles /></Authorized></Protected>} />
        <Route path="/audit" element={<Protected><Authorized permission="audit:read"><AuditLog /></Authorized></Protected>} />
        <Route path="/model-operations" element={<Protected><Authorized permission="platform:admin"><ModelOperations /></Authorized></Protected>} />
        <Route path="/tenants" element={<Protected><Authorized permission="platform:admin"><TenantManagement /></Authorized></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
