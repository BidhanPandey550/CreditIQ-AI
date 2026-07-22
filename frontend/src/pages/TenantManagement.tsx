import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Badge, Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Organization {
  id: string;
  name: string;
  type: string;
  status: string;
  nrb_license_no: string | null;
  created_at: string;
}

const input = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";

export default function TenantManagement() {
  const { me, switchOrganization } = useAuth();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", type: "mfi", email: "", fullName: "", password: "" });
  const [target, setTarget] = useState<Organization | null>(null);
  const [reason, setReason] = useState("");
  const organizations = useQuery({
    queryKey: ["platform-organizations"],
    queryFn: () => api.get<Organization[]>("/organizations"),
  });
  const onboard = useMutation({
    mutationFn: () => api.post("/organizations/onboard", {
      organization_name: form.name,
      organization_type: form.type,
      admin_email: form.email,
      admin_full_name: form.fullName,
      admin_password: form.password,
    }),
    onSuccess: () => {
      setForm({ name: "", type: "mfi", email: "", fullName: "", password: "" });
      void queryClient.invalidateQueries({ queryKey: ["platform-organizations"] });
    },
  });
  const updateStatus = useMutation({
    mutationFn: ({ organization, status }: { organization: Organization; status: "active" | "suspended" }) =>
      api.patch<Organization>(`/organizations/${organization.id}/status`, { status, reason }),
    onSuccess: () => {
      setTarget(null); setReason("");
      void queryClient.invalidateQueries({ queryKey: ["platform-organizations"] });
    },
  });

  function submit(event: FormEvent) { event.preventDefault(); onboard.mutate(); }

  return (
    <div className="space-y-6">
      <div><h1 className="text-xl font-semibold">Tenant Management</h1><p className="mt-1 text-sm text-slate-500">Platform-owner provisioning and lifecycle controls. Every mutation is audited.</p></div>
      <Card>
        <h2 className="font-medium">Onboard institution</h2>
        <form className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3" onSubmit={submit}>
          <label className="text-sm">Organization name<input className={`${input} mt-1`} minLength={2} required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="text-sm">Institution type<select className={`${input} mt-1`} value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}><option value="bank">Bank</option><option value="mfi">Microfinance institution</option><option value="cooperative">Cooperative</option><option value="digital_lender">Digital lender</option></select></label>
          <label className="text-sm">Administrator name<input className={`${input} mt-1`} minLength={2} required value={form.fullName} onChange={(event) => setForm({ ...form, fullName: event.target.value })} /></label>
          <label className="text-sm">Administrator email<input className={`${input} mt-1`} required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
          <label className="text-sm">Temporary password<input className={`${input} mt-1`} minLength={12} required type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>
          <div className="flex items-end"><Button disabled={onboard.isPending}>{onboard.isPending ? "Provisioning…" : "Onboard institution"}</Button></div>
        </form>
        {onboard.isError && <p className="mt-3 text-sm text-rose-600">{onboard.error.message}</p>}
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800"><tr><th className="px-4 py-3">Institution</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Created</th><th className="px-4 py-3"></th></tr></thead>
          <tbody>{organizations.data?.map((organization) => <tr key={organization.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800"><td className="px-4 py-3"><div className="font-medium">{organization.name}</div><div className="text-xs text-slate-500">{organization.id === me?.home_organization_id ? "Platform home" : organization.id}</div></td><td className="px-4 py-3 capitalize">{organization.type.replace(/_/g, " ")}</td><td className="px-4 py-3"><Badge label={organization.status} /></td><td className="px-4 py-3">{new Date(organization.created_at).toLocaleDateString()}</td><td className="px-4 py-3"><div className="flex gap-2"><Button variant="ghost" disabled={organization.status !== "active" || organization.id === me?.organization_id} onClick={() => switchOrganization(organization.id)}>{organization.id === me?.organization_id ? "Current" : "Open"}</Button>{organization.id !== me?.organization_id && <Button variant="ghost" onClick={() => { setTarget(organization); setReason(""); }}>{organization.status === "active" ? "Suspend" : "Reactivate"}</Button>}</div></td></tr>)}</tbody>
        </table>
      </Card>

      {target && <Card><h2 className="font-medium">{target.status === "active" ? "Suspend" : "Reactivate"} {target.name}</h2><p className="mt-1 text-sm text-slate-500">Provide an auditable reason. Suspended tenants cannot use access tokens.</p><textarea className={`${input} mt-4`} minLength={5} rows={3} value={reason} onChange={(event) => setReason(event.target.value)} /><div className="mt-3 flex gap-2"><Button disabled={reason.trim().length < 5 || updateStatus.isPending} onClick={() => updateStatus.mutate({ organization: target, status: target.status === "active" ? "suspended" : "active" })}>{updateStatus.isPending ? "Updating…" : "Confirm"}</Button><Button variant="ghost" onClick={() => setTarget(null)}>Cancel</Button></div>{updateStatus.isError && <p className="mt-2 text-sm text-rose-600">{updateStatus.error.message}</p>}</Card>}
    </div>
  );
}
