import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Button, Card, Stat } from "./ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Transaction {
  id: string;
  source_type: "bank" | "wallet" | "utility";
  txn_date: string;
  amount: number;
  description: string | null;
  is_simulated: boolean;
}

interface TransactionPage {
  items: Transaction[];
  total: number;
  total_credits: number;
  total_debits: number;
  net_cashflow: number;
  simulated_count: number;
}

function monthlyCashflow(items: Transaction[]) {
  const months = new Map<string, { month: string; credits: number; debits: number }>();
  for (const item of items) {
    const month = item.txn_date.slice(0, 7);
    const row = months.get(month) ?? { month, credits: 0, debits: 0 };
    if (item.amount >= 0) row.credits += item.amount;
    else row.debits += Math.abs(item.amount);
    months.set(month, row);
  }
  return [...months.values()].sort((left, right) => left.month.localeCompare(right.month)).slice(-6);
}

export default function ApplicantTransactions({ applicantId }: { applicantId: string }) {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const ledger = useQuery({
    queryKey: ["transactions", applicantId],
    queryFn: () => api.get<TransactionPage>(`/applicants/${applicantId}/transactions?limit=500`),
  });
  const regenerate = useMutation({
    mutationFn: () => api.post<{ created: number; replaced: number }>(`/applicants/${applicantId}/simulate-transactions`),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["transactions", applicantId] }),
        queryClient.invalidateQueries({ queryKey: ["financials", applicantId] }),
      ]);
    },
  });

  if (ledger.isLoading) return <p className="text-sm text-slate-500">Loading transaction evidence…</p>;
  if (ledger.isError) return <p className="text-sm text-rose-600">{ledger.error.message}</p>;
  if (!ledger.data) return null;

  const data = ledger.data;
  const chart = monthlyCashflow(data.items);
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-medium">Financial behaviour evidence</h2>
          <p className="mt-1 text-sm text-slate-500">Cash-flow history used by behavioural risk features.</p>
        </div>
        {can("applicant:manage") && (
          <Button variant="ghost" disabled={regenerate.isPending} onClick={() => regenerate.mutate()}>
            {regenerate.isPending ? "Generating…" : "Regenerate simulated wallet data"}
          </Button>
        )}
      </div>

      {data.simulated_count > 0 && (
        <Card className="border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
          <p className="text-sm text-amber-800 dark:text-amber-200">
            Simulated MVP evidence — not connected to a real bank or wallet. {data.simulated_count} of {data.total} records are synthetic.
          </p>
        </Card>
      )}
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Credits" value={`NPR ${data.total_credits.toLocaleString()}`} />
        <Stat label="Debits" value={`NPR ${data.total_debits.toLocaleString()}`} />
        <Stat label="Net cash flow" value={`NPR ${data.net_cashflow.toLocaleString()}`} />
      </div>

      {chart.length > 0 && (
        <Card>
          <h3 className="mb-3 text-sm font-medium">Monthly cash flow</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chart}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(value) => `NPR ${Number(value).toLocaleString()}`} />
              <Legend />
              <Bar dataKey="credits" fill="#10b981" />
              <Bar dataKey="debits" fill="#f43f5e" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800">
            <tr><th className="px-4 py-3">Date</th><th className="px-4 py-3">Description</th><th className="px-4 py-3">Source</th><th className="px-4 py-3 text-right">Amount</th></tr>
          </thead>
          <tbody>
            {data.items.slice(0, 20).map((item) => (
              <tr key={item.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                <td className="whitespace-nowrap px-4 py-3">{new Date(item.txn_date).toLocaleDateString()}</td>
                <td className="px-4 py-3">{item.description ?? "Transaction"}</td>
                <td className="px-4 py-3"><Badge label={`${item.source_type}${item.is_simulated ? " · simulated" : ""}`} /></td>
                <td className={`whitespace-nowrap px-4 py-3 text-right font-medium ${item.amount >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {item.amount >= 0 ? "+" : "−"} NPR {Math.abs(item.amount).toLocaleString()}
                </td>
              </tr>
            ))}
            {data.items.length === 0 && <tr><td colSpan={4} className="px-4 py-5 text-slate-500">No transaction evidence available.</td></tr>}
          </tbody>
        </table>
        {data.total > 20 && <p className="border-t border-slate-100 px-4 py-3 text-xs text-slate-500 dark:border-slate-800">Showing the latest 20 of {data.total} records.</p>}
      </Card>
      {regenerate.isError && <p className="text-sm text-rose-600">{regenerate.error.message}</p>}
    </section>
  );
}
