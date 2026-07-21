import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Button, Card, Stat } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import Dashboard from "./Dashboard";

interface ApplicantSummary {
  id: string;
  full_name: string;
}

interface LoanSummary {
  id: string;
  reference_no: string;
  amount: number;
  status: string;
}

function ApplicantDashboard() {
  const applicantQuery = useQuery({
    queryKey: ["applicant-self"],
    queryFn: () => api.get<ApplicantSummary[]>("/applicants"),
  });
  const loansQuery = useQuery({
    queryKey: ["loans-self"],
    queryFn: () => api.get<LoanSummary[]>("/loans"),
  });

  if (applicantQuery.isLoading || loansQuery.isLoading) {
    return <p className="text-slate-500">Loading your lending profile…</p>;
  }
  const error = applicantQuery.error || loansQuery.error;
  if (error) return <p className="text-rose-600">{(error as Error).message}</p>;

  const profile = applicantQuery.data?.[0];
  const loans = loansQuery.data ?? [];
  const active = loans.filter((loan) => ["disbursed", "active"].includes(loan.status)).length;
  const pending = loans.filter((loan) =>
    ["draft", "submitted", "under_review", "ai_risk_analysis", "fraud_screening", "officer_review", "risk_analyst_review", "needs_more_info"].includes(loan.status),
  ).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">Welcome, {profile?.full_name ?? "Applicant"}</h1>
          <p className="mt-1 text-sm text-slate-500">
            Track your applications and submit a new loan request securely.
          </p>
        </div>
        <Link to="/loans/new"><Button>New loan application</Button></Link>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Applications" value={loans.length} />
        <Stat label="Pending review" value={pending} />
        <Stat label="Active loans" value={active} />
      </div>
      <Card>
        <h2 className="mb-3 font-medium">Recent applications</h2>
        {loans.length === 0 ? (
          <p className="text-sm text-slate-500">No applications yet.</p>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {loans.slice(0, 5).map((loan) => (
              <Link key={loan.id} to={`/loans/${loan.id}`} className="flex items-center justify-between py-3 text-sm">
                <span className="font-medium">{loan.reference_no}</span>
                <span>NPR {loan.amount.toLocaleString()}</span>
                <span className="capitalize text-slate-500">{loan.status.replace(/_/g, " ")}</span>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

export default function Home() {
  const { me } = useAuth();
  return me?.roles.includes("Applicant") ? <ApplicantDashboard /> : <Dashboard />;
}
