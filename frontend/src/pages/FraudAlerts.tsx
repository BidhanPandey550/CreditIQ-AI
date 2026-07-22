import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface FraudAlert {
  id: string;
  loan_id: string;
  loan_reference: string;
  applicant_id: string;
  applicant_name: string;
  severity: string;
  status: string;
  reasons: string[];
  resolved_by: string | null;
  resolved_at: string | null;
  resolution_note: string | null;
  created_at: string;
}

export default function FraudAlerts() {
  const queryClient = useQueryClient();
  const { can } = useAuth();
  const [status, setStatus] = useState("open");
  const [selected, setSelected] = useState<FraudAlert | null>(null);
  const [resolution, setResolution] = useState<"confirmed" | "dismissed">("confirmed");
  const [note, setNote] = useState("");
  const alerts = useQuery({
    queryKey: ["fraud-alerts", status],
    queryFn: () => api.get<FraudAlert[]>(`/fraud/alerts${status ? `?status=${status}` : ""}`),
  });
  const resolve = useMutation({
    mutationFn: () => api.post<FraudAlert>(`/fraud/alerts/${selected?.id}/resolve`, {
      status: resolution,
      note,
    }),
    onSuccess: () => {
      setSelected(null);
      setNote("");
      void queryClient.invalidateQueries({ queryKey: ["fraud-alerts"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    resolve.mutate();
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">Fraud alert center</h1>
          <p className="mt-1 text-sm text-slate-500">Investigate lending anomalies with an auditable disposition.</p>
        </div>
        <label className="text-sm">Status
          <select className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="open">Open</option><option value="confirmed">Confirmed</option><option value="dismissed">Dismissed</option><option value="">All</option>
          </select>
        </label>
      </div>
      {alerts.isLoading && <p className="text-sm text-slate-500">Loading fraud alerts…</p>}
      {alerts.isError && <p className="text-sm text-rose-600">{alerts.error.message}</p>}
      {alerts.data?.length === 0 && <Card><p className="text-sm text-slate-500">No alerts match this status.</p></Card>}
      <div className="space-y-3">
        {alerts.data?.map((alert) => (
          <Card key={alert.id}>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2"><Badge label={alert.severity} /><Badge label={alert.status} /><Link className="font-medium text-brand hover:underline" to={`/loans/${alert.loan_id}`}>{alert.loan_reference}</Link></div>
                <p className="mt-2 text-sm font-medium">{alert.applicant_name}</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">{alert.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                <p className="mt-2 text-xs text-slate-400">Detected {new Date(alert.created_at).toLocaleString()}</p>
                {alert.resolution_note && <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800"><span className="font-medium">Resolution:</span> {alert.resolution_note}</p>}
              </div>
              {alert.status === "open" && can("fraud:resolve") && <Button onClick={() => setSelected(alert)}>Investigate</Button>}
            </div>
          </Card>
        ))}
      </div>
      {selected && <Card>
        <form className="space-y-4" onSubmit={submit}>
          <div><h2 className="font-semibold">Resolve {selected.loan_reference}</h2><p className="text-sm text-slate-500">The disposition and rationale become permanent audit evidence.</p></div>
          <label className="block text-sm">Disposition<select className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950" value={resolution} onChange={(event) => setResolution(event.target.value as "confirmed" | "dismissed")}><option value="confirmed">Confirm fraud concern</option><option value="dismissed">Dismiss false positive</option></select></label>
          <label className="block text-sm">Investigation rationale<textarea className="mt-1 min-h-28 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950" minLength={10} maxLength={2000} required value={note} onChange={(event) => setNote(event.target.value)} /></label>
          {resolve.error && <p className="text-sm text-rose-600">{resolve.error.message}</p>}
          <div className="flex gap-2"><Button disabled={resolve.isPending}>{resolve.isPending ? "Saving…" : "Save disposition"}</Button><Button type="button" variant="ghost" onClick={() => setSelected(null)}>Cancel</Button></div>
        </form>
      </Card>}
    </div>
  );
}
