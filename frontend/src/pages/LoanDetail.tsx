import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Badge, Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Loan {
  id: string;
  reference_no: string;
  amount: number;
  tenor_months: number;
  status: string;
}
interface Contribution {
  feature: string;
  impact: number;
  value: number;
}
interface Intelligence {
  risk: { band: string; probability: number } | null;
  credit_score: { score: number; subscores: Record<string, number> } | null;
  default: { probability: number; horizon_months: number } | null;
  fraud_alerts: { severity: string; status: string; reasons: string[] }[];
  explanation: { narrative: string; shap_contributions: Contribution[] } | null;
}

export default function LoanDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
  const { can } = useAuth();

  const loan = useQuery({ queryKey: ["loan", id], queryFn: () => api.get<Loan>(`/loans/${id}`) });
  const intel = useQuery({
    queryKey: ["intel", id],
    queryFn: () => api.get<Intelligence>(`/loans/${id}/intelligence`),
  });

  const history = useQuery({
    queryKey: ["history", id],
    queryFn: () =>
      api.get<{ from_status: string | null; to_status: string; reason: string | null; created_at: string }[]>(
        `/loans/${id}/history`,
      ),
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["intel", id] });
    qc.invalidateQueries({ queryKey: ["loan", id] });
    qc.invalidateQueries({ queryKey: ["history", id] });
  };

  const analyze = useMutation({
    mutationFn: () => api.post(`/loans/${id}/analyze`),
    onSuccess: invalidateAll,
  });
  const submit = useMutation({ mutationFn: () => api.post(`/loans/${id}/submit`), onSuccess: invalidateAll });
  const disburse = useMutation({ mutationFn: () => api.post(`/loans/${id}/disburse`), onSuccess: invalidateAll });
  const decide = useMutation({
    mutationFn: (decision: string) => api.post(`/loans/${id}/decision`, { decision }),
    onSuccess: invalidateAll,
  });

  if (loan.isLoading) return <p className="text-slate-500">Loading…</p>;
  const i = intel.data;
  const status = loan.data?.status ?? "";
  const inReview = status === "officer_review" || status === "analyst_review";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{loan.data?.reference_no}</h1>
          <p className="text-sm text-slate-500">
            NPR {loan.data?.amount.toLocaleString()} · {loan.data?.tenor_months} months ·{" "}
            <span className="capitalize">{loan.data?.status.replace(/_/g, " ")}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {status === "draft" && can("loan:create") && (
            <Button onClick={() => submit.mutate()} disabled={submit.isPending}>
              Submit for review
            </Button>
          )}
          {status === "under_review" && can("loan:review") && (
            <Button onClick={() => analyze.mutate()} disabled={analyze.isPending}>
              {analyze.isPending ? "Running AI analysis…" : "Run AI Analysis"}
            </Button>
          )}
          {inReview && can("loan:approve") && (
            <>
              <Button onClick={() => decide.mutate("approve")} disabled={decide.isPending}>
                Approve
              </Button>
              <Button variant="ghost" onClick={() => decide.mutate("reject")} disabled={decide.isPending}>
                Reject
              </Button>
              <Button variant="ghost" onClick={() => decide.mutate("needs_more_info")} disabled={decide.isPending}>
                Needs info
              </Button>
            </>
          )}
          {status === "approved" && can("loan:disburse") && (
            <Button onClick={() => disburse.mutate()} disabled={disburse.isPending}>
              Disburse
            </Button>
          )}
        </div>
      </div>

      {[submit, analyze, decide, disburse].map((m, idx) =>
        m.isError ? (
          <p key={idx} className="text-sm text-rose-600">
            {(m.error as Error).message}
          </p>
        ) : null,
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <div className="text-sm text-slate-500">Credit Score</div>
          <div className="mt-1 text-4xl font-bold">{i?.credit_score?.score ?? "—"}</div>
          <div className="text-xs text-slate-400">out of 100</div>
          {i?.credit_score && (
            <div className="mt-3 space-y-1 text-sm">
              {Object.entries(i.credit_score.subscores).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="capitalize text-slate-500">{k}</span>
                  <span>{v}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <div className="text-sm text-slate-500">Risk Band</div>
          <div className="mt-2">
            {i?.risk ? <Badge label={i.risk.band} /> : <span className="text-slate-400">—</span>}
          </div>
          <div className="mt-4 text-sm text-slate-500">Default Probability (12m)</div>
          <div className="text-2xl font-semibold">
            {i?.default ? `${(i.default.probability * 100).toFixed(1)}%` : "—"}
          </div>
        </Card>

        <Card>
          <div className="text-sm text-slate-500">Fraud Screening</div>
          {i?.fraud_alerts.length ? (
            <div className="mt-2 space-y-2">
              {i.fraud_alerts.map((f, idx) => (
                <div key={idx}>
                  <Badge label={f.severity} />
                  <ul className="mt-1 list-disc pl-5 text-xs text-slate-500">
                    {f.reasons.map((r, j) => (
                      <li key={j}>{r}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-2 text-sm text-emerald-600">No alerts</div>
          )}
        </Card>
      </div>

      <Card>
        <h2 className="font-medium">Explainable AI (SHAP)</h2>
        {i?.explanation ? (
          <>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {i.explanation.narrative}
            </p>
            <div className="mt-4 space-y-2">
              {i.explanation.shap_contributions.map((c) => {
                const positive = c.impact > 0; // increases default risk
                const width = Math.min(100, Math.abs(c.impact) * 400);
                return (
                  <div key={c.feature} className="flex items-center gap-3 text-sm">
                    <span className="w-44 capitalize text-slate-500">
                      {c.feature.replace(/_/g, " ")}
                    </span>
                    <div className="flex-1">
                      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                        <div
                          className={`h-2 rounded-full ${positive ? "bg-rose-500" : "bg-emerald-500"}`}
                          style={{ width: `${width}%` }}
                        />
                      </div>
                    </div>
                    <span className="w-16 text-right text-slate-400">{c.impact.toFixed(3)}</span>
                  </div>
                );
              })}
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Red = increases default risk · Green = reduces default risk
            </p>
          </>
        ) : (
          <p className="mt-2 text-sm text-slate-500">
            No analysis yet. Run AI analysis to generate an explainable assessment.
          </p>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 font-medium">Workflow Timeline</h2>
        {history.data?.length ? (
          <ol className="relative ml-2 border-l border-slate-200 dark:border-slate-700">
            {history.data.map((e, idx) => (
              <li key={idx} className="mb-4 ml-4">
                <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-brand" />
                <div className="text-sm font-medium capitalize">
                  {e.to_status.replace(/_/g, " ")}
                </div>
                <div className="text-xs text-slate-400">
                  {new Date(e.created_at).toLocaleString()}
                  {e.reason ? ` · ${e.reason}` : ""}
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-slate-500">No workflow events yet.</p>
        )}
      </Card>
    </div>
  );
}
