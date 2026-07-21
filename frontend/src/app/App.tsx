import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../lib/auth";
import Applicants from "../pages/Applicants";
import Dashboard from "../pages/Dashboard";
import LoanDetail from "../pages/LoanDetail";
import Loans from "../pages/Loans";
import Login from "../pages/Login";
import NewApplicant from "../pages/NewApplicant";
import NewLoan from "../pages/NewLoan";

function Protected({ children }: { children: React.ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <div className="grid min-h-screen place-items-center text-slate-500">Loading…</div>;
  if (!me) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
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
  );
}
