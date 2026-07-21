import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../lib/auth";

const Applicants = lazy(() => import("../pages/Applicants"));
const Dashboard = lazy(() => import("../pages/Dashboard"));
const LoanDetail = lazy(() => import("../pages/LoanDetail"));
const Loans = lazy(() => import("../pages/Loans"));
const Login = lazy(() => import("../pages/Login"));
const NewApplicant = lazy(() => import("../pages/NewApplicant"));
const NewLoan = lazy(() => import("../pages/NewLoan"));

function LoadingScreen() {
  return <div className="grid min-h-screen place-items-center text-slate-500">Loading…</div>;
}

function Protected({ children }: { children: React.ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!me) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Suspense fallback={<LoadingScreen />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Protected><Dashboard /></Protected>} />
        <Route path="/loans" element={<Protected><Loans /></Protected>} />
        <Route path="/loans/new" element={<Protected><NewLoan /></Protected>} />
        <Route path="/loans/:id" element={<Protected><LoanDetail /></Protected>} />
        <Route path="/applicants" element={<Protected><Applicants /></Protected>} />
        <Route path="/applicants/new" element={<Protected><NewApplicant /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
