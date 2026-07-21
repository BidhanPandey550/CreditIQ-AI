import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Card } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface AuditEvent {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  request_id: string | null;
  created_at: string;
}

export default function AuditLog() {
  const { can } = useAuth();
  const [action, setAction] = useState("");
  const events = useQuery({
    queryKey: ["audit", action],
    queryFn: () =>
      api.get<AuditEvent[]>(`/audit?limit=100${action ? `&action=${encodeURIComponent(action)}` : ""}`),
    enabled: can("audit:read"),
  });

  if (!can("audit:read")) {
    return <p className="text-sm text-amber-600">Audit permission is required.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">Compliance Audit Log</h1>
          <p className="mt-1 text-sm text-slate-500">
            Immutable, tenant-scoped records of sensitive platform actions.
          </p>
        </div>
        <label className="text-sm text-slate-500">
          Action filter
          <input
            value={action}
            onChange={(event) => setAction(event.target.value)}
            placeholder="loan.transition"
            className="mt-1 block rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
          />
        </label>
      </div>
      {events.isLoading && <p className="text-sm text-slate-500">Loading audit records…</p>}
      {events.isError && <p className="text-sm text-rose-600">{(events.error as Error).message}</p>}
      <Card className="overflow-x-auto p-0">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500 dark:border-slate-800">
            <tr><th className="p-4">Time</th><th className="p-4">Action</th><th className="p-4">Entity</th><th className="p-4">Actor</th><th className="p-4">Request</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {events.data?.map((event) => (
              <tr key={event.id}>
                <td className="whitespace-nowrap p-4 text-slate-500">{new Date(event.created_at).toLocaleString()}</td>
                <td className="p-4 font-medium">{event.action}</td>
                <td className="p-4 text-slate-500">{event.entity_type ?? "—"}<br /><span className="text-xs">{event.entity_id ?? ""}</span></td>
                <td className="p-4 text-xs text-slate-500">{event.actor_user_id ?? "system"}</td>
                <td className="p-4 text-xs text-slate-500">{event.request_id ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {events.data?.length === 0 && <p className="p-6 text-center text-sm text-slate-500">No audit records match this filter.</p>}
      </Card>
    </div>
  );
}
