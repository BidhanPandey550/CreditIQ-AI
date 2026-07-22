import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Badge, Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";

interface OrganizationRecord { id: string; name: string; type: string; status: string; nrb_license_no: string | null; settings: { currency?: string; timezone?: string; fiscal_year_start_month?: number } }
interface Branch { id: string; name: string; code: string; address: string | null; status: string }
const inputClass = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";

export default function Organization() {
  const queryClient = useQueryClient();
  const organization = useQuery({ queryKey: ["organization"], queryFn: () => api.get<OrganizationRecord>("/organizations/me") });
  const branches = useQuery({ queryKey: ["branches"], queryFn: () => api.get<Branch[]>("/organizations/branches") });
  const [name, setName] = useState("");
  const [license, setLicense] = useState("");
  const [currency, setCurrency] = useState("NPR");
  const [timezone, setTimezone] = useState("Asia/Kathmandu");
  const [fiscalMonth, setFiscalMonth] = useState(4);
  const [branchName, setBranchName] = useState("");
  const [branchCode, setBranchCode] = useState("");
  const [branchAddress, setBranchAddress] = useState("");

  useEffect(() => {
    if (!organization.data) return;
    setName(organization.data.name);
    setLicense(organization.data.nrb_license_no ?? "");
    setCurrency(organization.data.settings.currency ?? "NPR");
    setTimezone(organization.data.settings.timezone ?? "Asia/Kathmandu");
    setFiscalMonth(organization.data.settings.fiscal_year_start_month ?? 4);
  }, [organization.data]);

  const saveOrganization = useMutation({
    mutationFn: () => api.put<OrganizationRecord>("/organizations/me", { name, nrb_license_no: license || null, settings: { currency, timezone, fiscal_year_start_month: fiscalMonth } }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["organization"] }),
  });
  const createBranch = useMutation({
    mutationFn: () => api.post<Branch>("/organizations/branches", { name: branchName, code: branchCode, address: branchAddress || null }),
    onSuccess: () => {
      setBranchName(""); setBranchCode(""); setBranchAddress("");
      void queryClient.invalidateQueries({ queryKey: ["branches"] });
    },
  });
  const updateBranch = useMutation({
    mutationFn: ({ branch, status }: { branch: Branch; status: string }) => api.put<Branch>(`/organizations/branches/${branch.id}`, { name: branch.name, address: branch.address, status }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["branches"] }),
  });

  function submitBranch(event: FormEvent) { event.preventDefault(); createBranch.mutate(); }

  return <div className="space-y-5">
    <div><h1 className="text-xl font-semibold">Organization settings</h1><p className="mt-1 text-sm text-slate-500">Manage tenant identity and operational branches. Changes are written to the compliance audit log.</p></div>
    <Card><h2 className="font-medium">Institution profile</h2><div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3"><label className="text-sm">Organization name<input className={`${inputClass} mt-1`} value={name} onChange={(event) => setName(event.target.value)} /></label><label className="text-sm">NRB license number<input className={`${inputClass} mt-1`} value={license} onChange={(event) => setLicense(event.target.value)} /></label><label className="text-sm">Currency<input className={`${inputClass} mt-1`} maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value)} /></label><label className="text-sm">IANA timezone<input className={`${inputClass} mt-1`} value={timezone} onChange={(event) => setTimezone(event.target.value)} /></label><label className="text-sm">Fiscal year start month<input className={`${inputClass} mt-1`} min={1} max={12} type="number" value={fiscalMonth} onChange={(event) => setFiscalMonth(Number(event.target.value))} /></label><div className="flex items-end"><Button disabled={saveOrganization.isPending || name.length < 2} onClick={() => saveOrganization.mutate()}>{saveOrganization.isPending ? "Saving…" : "Save settings"}</Button></div></div>{saveOrganization.error && <p className="mt-2 text-sm text-rose-600">{saveOrganization.error.message}</p>}</Card>
    <Card><h2 className="font-medium">Add branch</h2><form className="mt-4 grid gap-4 md:grid-cols-4" onSubmit={submitBranch}><label className="text-sm">Name<input className={`${inputClass} mt-1`} required value={branchName} onChange={(event) => setBranchName(event.target.value)} /></label><label className="text-sm">Code<input className={`${inputClass} mt-1`} required value={branchCode} onChange={(event) => setBranchCode(event.target.value)} /></label><label className="text-sm">Address<input className={`${inputClass} mt-1`} value={branchAddress} onChange={(event) => setBranchAddress(event.target.value)} /></label><div className="flex items-end"><Button disabled={createBranch.isPending}>{createBranch.isPending ? "Adding…" : "Add branch"}</Button></div></form>{createBranch.error && <p className="mt-2 text-sm text-rose-600">{createBranch.error.message}</p>}</Card>
    <Card className="overflow-x-auto p-0"><table className="w-full text-sm"><thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800"><tr><th className="px-4 py-3">Branch</th><th className="px-4 py-3">Code</th><th className="px-4 py-3">Address</th><th className="px-4 py-3">Status</th><th className="px-4 py-3"></th></tr></thead><tbody>{branches.data?.map((branch) => <tr key={branch.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800"><td className="px-4 py-3 font-medium">{branch.name}</td><td className="px-4 py-3">{branch.code}</td><td className="px-4 py-3">{branch.address ?? "—"}</td><td className="px-4 py-3"><Badge label={branch.status} /></td><td className="px-4 py-3"><Button variant="ghost" disabled={updateBranch.isPending} onClick={() => updateBranch.mutate({ branch, status: branch.status === "active" ? "inactive" : "active" })}>{branch.status === "active" ? "Deactivate" : "Activate"}</Button></td></tr>)}</tbody></table></Card>
  </div>;
}
