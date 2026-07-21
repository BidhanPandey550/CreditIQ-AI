import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Badge, Button, Card } from "../components/ui/primitives";
import { api, tokenStore } from "../lib/api";
import { useAuth } from "../lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function downloadCsv() {
  const res = await fetch(`${API_BASE}/reports/loans.csv`, {
    headers: { Authorization: `Bearer ${tokenStore.access}` },
  });
  if (!res.ok) return;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "loans_export.csv";
  a.click();
  URL.revokeObjectURL(url);
}

interface Loan {
  id: string;
  reference_no: string;
  amount: number;
  tenor_months: number;
  status: string;
  created_at: string;
}

const statusTone: Record<string, string> = {
  approved: "low",
  disbursed: "low",
  active: "low",
  rejected: "high",
  defaulted: "high",
};

export default function Loans() {
  const { can } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: ["loans"],
    queryFn: () => api.get<Loan[]>("/loans"),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Loan Applications</h1>
        <div className="flex gap-2">
          {can("report:export") && (
            <Button variant="ghost" onClick={downloadCsv}>
              Export CSV
            </Button>
          )}
          {can("loan:create") && (
            <Link to="/loans/new">
              <Button>New Loan</Button>
            </Link>
          )}
        </div>
      </div>
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800">
            <tr>
              <th className="px-4 py-3">Reference</th>
              <th className="px-4 py-3">Amount (NPR)</th>
              <th className="px-4 py-3">Tenor</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td className="px-4 py-4 text-slate-500" colSpan={5}>
                  Loading…
                </td>
              </tr>
            )}
            {data?.map((loan) => (
              <tr
                key={loan.id}
                className="border-b border-slate-100 last:border-0 dark:border-slate-800"
              >
                <td className="px-4 py-3 font-medium">{loan.reference_no}</td>
                <td className="px-4 py-3">{loan.amount.toLocaleString()}</td>
                <td className="px-4 py-3">{loan.tenor_months} mo</td>
                <td className="px-4 py-3">
                  <Badge label={statusTone[loan.status] ?? loan.status.replace(/_/g, " ")} />
                </td>
                <td className="px-4 py-3 text-right">
                  <Link to={`/loans/${loan.id}`} className="text-brand hover:underline">
                    View →
                  </Link>
                </td>
              </tr>
            ))}
            {data?.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-500" colSpan={5}>
                  No loan applications yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
