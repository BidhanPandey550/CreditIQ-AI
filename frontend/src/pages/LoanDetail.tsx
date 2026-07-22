import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
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
  decision: {
    recommendation: string;
    confidence: number;
    credit_risk: string;
    fraud_risk: string | null;
    decision_reasons: string[];
    warnings: string[];
    monitoring_status: string;
    created_at: string;
  } | null;
}
interface Servicing {
  original_principal: number;
  total_due: number;
  total_paid: number;
  outstanding: number;
  overdue_amount: number;
  days_past_due: number;
  next_due_date: string | null;
  installments: {
    id: string;
    sequence_no: number;
    due_date: string;
    principal_due: number;
    interest_due: number;
    principal_paid: number;
    interest_paid: number;
    outstanding: number;
    days_past_due: number;
  }[];
  repayments: { id: string; amount: number; paid_at: string; external_reference: string | null }[];
}

export default function LoanDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
  const { can } = useAuth();
  const [interestRate, setInterestRate] = useState("");
  const [firstDueDate, setFirstDueDate] = useState("");
  const [disbursementReference, setDisbursementReference] = useState("");
  const [repaymentAmount, setRepaymentAmount] = useState("");
  const [repaymentReference, setRepaymentReference] = useState("");

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
  const servicing = useQuery({
    queryKey: ["servicing", id],
    queryFn: () => api.get<Servicing>(`/loans/${id}/servicing`),
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["intel", id] });
    qc.invalidateQueries({ queryKey: ["loan", id] });
    qc.invalidateQueries({ queryKey: ["history", id] });
    qc.invalidateQueries({ queryKey: ["servicing", id] });
  };

  const analyze = useMutation({
    mutationFn: () => api.post(`/loans/${id}/analyze`),
    onSuccess: invalidateAll,
  });
  const submit = useMutation({ mutationFn: () => api.post(`/loans/${id}/submit`), onSuccess: invalidateAll });
  const disburse = useMutation({
    mutationFn: () => api.post(`/loans/${id}/disburse`, {
      annual_interest_rate: interestRate ? Number(interestRate) : null,
      first_due_date: firstDueDate || null,
      external_reference: disbursementReference || null,
    }),
    onSuccess: invalidateAll,
  });
  const repay = useMutation({
    mutationFn: () => api.post(`/loans/${id}/repayments`, {
      amount: Number(repaymentAmount),
      external_reference: repaymentReference || null,
    }),
    onSuccess: () => {
      setRepaymentAmount("");
      setRepaymentReference("");
      invalidateAll();
    },
  });
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
        </div>
      </div>

      {[submit, analyze, decide, disburse, repay].map((m, idx) =>
        m.isError ? (
          <p key={idx} className="text-sm text-rose-600">
            {(m.error as Error).message}
          </p>
        ) : null,
      )}

      {status === "approved" && can("loan:disburse") && (
        <Card>
          <h2 className="font-medium">Disbursement terms</h2>
          <p className="mt-1 text-sm text-slate-500">Confirm the contractual rate and first due date. Leaving the rate empty uses the configured loan product or institutional default.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <label className="text-sm">Annual interest (%)<input className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700" min="0" max="100" step="0.01" type="number" value={interestRate} onChange={(event) => setInterestRate(event.target.value)} /></label>
            <label className="text-sm">First due date<input className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700" type="date" value={firstDueDate} onChange={(event) => setFirstDueDate(event.target.value)} /></label>
            <label className="text-sm">External reference<input className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700" value={disbursementReference} onChange={(event) => setDisbursementReference(event.target.value)} /></label>
            <div className="flex items-end"><Button onClick={() => disburse.mutate()} disabled={disburse.isPending}>{disburse.isPending ? "Disbursing…" : "Disburse loan"}</Button></div>
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <div className="text-sm text-slate-500">Credit Score</div>
          <div className="mt-1 text-4xl font-bold">{i?.credit_score?.score ?? "—"}</div>
          <div className="text-xs text-slate-400">300–850 range</div>
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
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-medium">AI Decision Support</h2>
            <p className="mt-1 text-xs text-slate-500">
              Advisory only. A duly authorized reviewer remains responsible for the lending decision.
            </p>
          </div>
          {i?.decision ? <Badge label={i.decision.recommendation.replace(/_/g, " ")} /> : null}
        </div>
        {i?.decision ? (
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div><div className="text-xs text-slate-500">Confidence</div><div className="text-2xl font-semibold">{(i.decision.confidence * 100).toFixed(1)}%</div></div>
            <div><div className="text-xs text-slate-500">Credit risk</div><div className="mt-1 capitalize">{i.decision.credit_risk.replace(/_/g, " ")}</div></div>
            <div><div className="text-xs text-slate-500">Fraud risk</div><div className="mt-1 capitalize">{i.decision.fraud_risk?.replace(/_/g, " ") ?? "Unavailable"}</div></div>
            <div className="md:col-span-3">
              <div className="text-xs text-slate-500">Policy reasons</div>
              <ul className="mt-1 list-disc pl-5 text-sm text-slate-600 dark:text-slate-300">
                {i.decision.decision_reasons.map((reason) => <li key={reason}>{reason.replace(/_/g, " ")}</li>)}
              </ul>
              {i.decision.warnings.length > 0 && <p className="mt-2 text-sm text-amber-600">Warnings: {i.decision.warnings.join(", ")}</p>}
            </div>
          </div>
        ) : <p className="mt-3 text-sm text-slate-500">Run AI analysis to generate a governed recommendation.</p>}
      </Card>

      <Card>
        <h2 className="font-medium">Explainable AI</h2>
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

      {["active", "defaulted", "closed"].includes(status) && (
        <Card className="overflow-x-auto">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="font-medium">Loan servicing</h2>
              <div className="mt-2 flex flex-wrap gap-4 text-sm">
                <span>Outstanding: <strong>NPR {(servicing.data?.outstanding ?? 0).toLocaleString()}</strong></span>
                <span>Paid: <strong>NPR {(servicing.data?.total_paid ?? 0).toLocaleString()}</strong></span>
                <span className={servicing.data?.days_past_due ? "text-rose-600" : "text-slate-500"}>DPD: <strong>{servicing.data?.days_past_due ?? 0}</strong></span>
              </div>
            </div>
            {can("loan:service") && status !== "closed" && <div className="flex flex-wrap gap-2"><input aria-label="Repayment amount" className="w-36 rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700" min="0.01" step="0.01" type="number" placeholder="Amount" value={repaymentAmount} onChange={(event) => setRepaymentAmount(event.target.value)} /><input aria-label="Repayment reference" className="w-44 rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700" placeholder="Reference" value={repaymentReference} onChange={(event) => setRepaymentReference(event.target.value)} /><Button disabled={repay.isPending || Number(repaymentAmount) <= 0} onClick={() => repay.mutate()}>{repay.isPending ? "Recording…" : "Record payment"}</Button></div>}
          </div>
          <table className="mt-4 w-full text-sm"><thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800"><tr><th className="py-2">#</th><th>Due date</th><th>Principal</th><th>Interest</th><th>Outstanding</th><th>DPD</th></tr></thead><tbody>{servicing.data?.installments.map((item) => <tr key={item.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800"><td className="py-2">{item.sequence_no}</td><td>{new Date(`${item.due_date}T00:00:00`).toLocaleDateString()}</td><td>NPR {item.principal_due.toLocaleString()}</td><td>NPR {item.interest_due.toLocaleString()}</td><td>NPR {item.outstanding.toLocaleString()}</td><td className={item.days_past_due ? "text-rose-600" : ""}>{item.days_past_due}</td></tr>)}</tbody></table>
        </Card>
      )}

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
