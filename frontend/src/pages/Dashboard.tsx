import { useQuery } from "@tanstack/react-query";
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Card, Stat } from "../components/ui/primitives";
import { api } from "../lib/api";

interface Overview {
  total_applications: number;
  approved: number;
  rejected: number;
  pending: number;
  approval_rate: number;
  average_credit_score: number | null;
  risk_distribution: { low: number; medium: number; high: number };
  portfolio_exposure: number;
}

const RISK_COLORS = { low: "#10b981", medium: "#f59e0b", high: "#f43f5e" };

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["overview"],
    queryFn: () => api.get<Overview>("/analytics/overview"),
  });

  if (isLoading) return <p className="text-slate-500">Loading analytics…</p>;
  if (error) return <p className="text-rose-600">{(error as Error).message}</p>;
  if (!data) return null;

  const riskData = [
    { name: "Low", value: data.risk_distribution.low, key: "low" },
    { name: "Medium", value: data.risk_distribution.medium, key: "medium" },
    { name: "High", value: data.risk_distribution.high, key: "high" },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Portfolio Overview</h1>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Total Applications" value={data.total_applications} />
        <Stat
          label="Approval Rate"
          value={`${Math.round(data.approval_rate * 100)}%`}
          hint={`${data.approved} approved`}
        />
        <Stat
          label="Avg Credit Score"
          value={data.average_credit_score ?? "—"}
          hint="300–850 credit score"
        />
        <Stat
          label="Portfolio Exposure"
          value={`NPR ${data.portfolio_exposure.toLocaleString()}`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-2 font-medium">Risk Distribution</h2>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={riskData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
                {riskData.map((d) => (
                  <Cell key={d.key} fill={RISK_COLORS[d.key as keyof typeof RISK_COLORS]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 flex justify-center gap-4 text-sm">
            {riskData.map((d) => (
              <span key={d.key} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ background: RISK_COLORS[d.key as keyof typeof RISK_COLORS] }}
                />
                {d.name}: {d.value}
              </span>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="mb-3 font-medium">Decision Funnel</h2>
          <div className="space-y-3">
            {[
              { label: "Approved", value: data.approved, color: "bg-emerald-500" },
              { label: "Rejected", value: data.rejected, color: "bg-rose-500" },
              { label: "Pending", value: data.pending, color: "bg-amber-500" },
            ].map((row) => {
              const pct = data.total_applications
                ? (row.value / data.total_applications) * 100
                : 0;
              return (
                <div key={row.label}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span>{row.label}</span>
                    <span className="text-slate-500">{row.value}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                    <div
                      className={`h-2 rounded-full ${row.color}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
