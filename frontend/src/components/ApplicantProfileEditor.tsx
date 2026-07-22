import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Button, Card } from "./ui/primitives";
import { api } from "../lib/api";

type MoneyRow = { source?: string; category?: string; name?: string; amount?: number; value?: number; outstanding_amount?: number; monthly_payment?: number | null; monthly_installment?: number | null; lender?: string | null; frequency?: string; is_delinquent?: boolean };
interface Profile {
  id: string; branch_id: string | null; full_name: string; date_of_birth: string | null; gender: string | null;
  phone: string | null; email: string | null; address: string | null; is_self_employed: boolean;
  national_id: string | null; kyc_verification_status: string | null;
  employment: { employer_name: string | null; position: string | null; monthly_income: number | null; employment_months: number | null } | null;
  business: { business_name: string | null; business_type: string | null; monthly_revenue: number | null; years_operating: number | null } | null;
  incomes: MoneyRow[]; expenses: MoneyRow[]; assets: MoneyRow[]; liabilities: MoneyRow[]; existing_loans: MoneyRow[];
}

const input = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";
const blank = (kind: string): MoneyRow => kind === "incomes" ? { source: "", amount: 0, frequency: "monthly" } : kind === "expenses" ? { category: "", amount: 0, frequency: "monthly" } : kind === "assets" ? { name: "", category: "", value: 0 } : kind === "liabilities" ? { name: "", outstanding_amount: 0, monthly_payment: 0 } : { lender: "", outstanding_amount: 0, monthly_installment: 0, is_delinquent: false };

export default function ApplicantProfileEditor({ applicantId }: { applicantId: string }) {
  const queryClient = useQueryClient();
  const profile = useQuery({ queryKey: ["applicant-profile", applicantId], queryFn: () => api.get<Profile>(`/applicants/${applicantId}/profile`) });
  const [draft, setDraft] = useState<Profile | null>(null);
  useEffect(() => { if (profile.data) setDraft(structuredClone(profile.data)); }, [profile.data]);
  const save = useMutation({
    mutationFn: () => api.patch<Profile>(`/applicants/${applicantId}/profile`, draft ? {
      ...draft,
      employment: draft.is_self_employed ? null : draft.employment,
      business: draft.is_self_employed ? draft.business : null,
    } : null),
    onSuccess: (updated) => {
      setDraft(updated);
      queryClient.setQueryData(["applicant-profile", applicantId], updated);
      void queryClient.invalidateQueries({ queryKey: ["applicant", applicantId] });
      void queryClient.invalidateQueries({ queryKey: ["financials", applicantId] });
    },
  });
  if (profile.isLoading || !draft) return <Card><p className="text-sm text-slate-500">Loading editable profile…</p></Card>;
  if (profile.error) return <Card><p className="text-sm text-rose-600">{profile.error.message}</p></Card>;
  const set = (field: keyof Profile, value: unknown) => setDraft((current) => current ? { ...current, [field]: value } : current);
  const updateRow = (kind: "incomes" | "expenses" | "assets" | "liabilities" | "existing_loans", index: number, field: string, value: unknown) => setDraft((current) => current ? { ...current, [kind]: current[kind].map((row, rowIndex) => rowIndex === index ? { ...row, [field]: value } : row) } : current);
  const removeRow = (kind: "incomes" | "expenses" | "assets" | "liabilities" | "existing_loans", index: number) => setDraft((current) => current ? { ...current, [kind]: current[kind].filter((_, rowIndex) => rowIndex !== index) } : current);
  const addRow = (kind: "incomes" | "expenses" | "assets" | "liabilities" | "existing_loans") => setDraft((current) => current ? { ...current, [kind]: [...current[kind], blank(kind)] } : current);
  const submit = (event: FormEvent) => { event.preventDefault(); save.mutate(); };

  return <Card><form className="space-y-6" onSubmit={submit}>
    <div><h2 className="font-semibold">Maintain underwriting profile</h2><p className="mt-1 text-sm text-slate-500">All changes are tenant-scoped and recorded with full before/after audit evidence.</p></div>
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <label className="text-sm">Full name<input className={input} required value={draft.full_name} onChange={(event) => set("full_name", event.target.value)} /></label>
      <label className="text-sm">Phone<input className={input} value={draft.phone ?? ""} onChange={(event) => set("phone", event.target.value || null)} /></label>
      <label className="text-sm">Email<input className={input} type="email" value={draft.email ?? ""} onChange={(event) => set("email", event.target.value || null)} /></label>
      <label className="text-sm">Date of birth<input className={input} type="date" value={draft.date_of_birth ?? ""} onChange={(event) => set("date_of_birth", event.target.value || null)} /></label>
      <label className="text-sm">National ID<input className={input} value={draft.national_id ?? ""} onChange={(event) => set("national_id", event.target.value || null)} /></label>
      <label className="text-sm">Employment type<select className={input} value={draft.is_self_employed ? "self" : "salaried"} onChange={(event) => set("is_self_employed", event.target.value === "self")}><option value="salaried">Salaried</option><option value="self">Self-employed</option></select></label>
      <label className="text-sm xl:col-span-3">Address<input className={input} value={draft.address ?? ""} onChange={(event) => set("address", event.target.value || null)} /></label>
    </div>
    {!draft.is_self_employed ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"><h3 className="font-medium md:col-span-2 xl:col-span-4">Employment</h3>{[["employer_name", "Employer"], ["position", "Position"], ["monthly_income", "Monthly income"], ["employment_months", "Employment months"]].map(([field, label]) => <label className="text-sm" key={field}>{label}<input className={input} type={field.includes("income") || field.includes("months") ? "number" : "text"} min="0" value={(draft.employment?.[field as keyof NonNullable<Profile["employment"]>] ?? "") as string | number} onChange={(event) => set("employment", { ...(draft.employment ?? { employer_name: null, position: null, monthly_income: null, employment_months: null }), [field]: event.target.type === "number" ? Number(event.target.value) : event.target.value || null })} /></label>)}</div> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"><h3 className="font-medium md:col-span-2 xl:col-span-4">Business</h3>{[["business_name", "Business name"], ["business_type", "Business type"], ["monthly_revenue", "Monthly revenue"], ["years_operating", "Years operating"]].map(([field, label]) => <label className="text-sm" key={field}>{label}<input className={input} type={field.includes("revenue") || field.includes("years") ? "number" : "text"} min="0" value={(draft.business?.[field as keyof NonNullable<Profile["business"]>] ?? "") as string | number} onChange={(event) => set("business", { ...(draft.business ?? { business_name: null, business_type: null, monthly_revenue: null, years_operating: null }), [field]: event.target.type === "number" ? Number(event.target.value) : event.target.value || null })} /></label>)}</div>}
    {(["incomes", "expenses", "assets", "liabilities", "existing_loans"] as const).map((kind) => <div key={kind} className="space-y-3"><div className="flex items-center justify-between"><h3 className="font-medium capitalize">{kind.replace("_", " ")}</h3><Button type="button" variant="ghost" onClick={() => addRow(kind)}>Add</Button></div>{draft[kind].map((row, index) => <div className="grid gap-2 rounded-lg border border-slate-200 p-3 md:grid-cols-4 dark:border-slate-800" key={`${kind}-${index}`}>{Object.entries(row).map(([field, value]) => <label className="text-xs capitalize" key={field}>{field.replace(/_/g, " ")}<input className={input} type={typeof value === "number" ? "number" : typeof value === "boolean" ? "checkbox" : "text"} min={typeof value === "number" ? 0 : undefined} checked={typeof value === "boolean" ? value : undefined} value={typeof value === "boolean" ? undefined : value ?? ""} onChange={(event) => updateRow(kind, index, field, typeof value === "number" ? Number(event.target.value) : typeof value === "boolean" ? event.target.checked : event.target.value)} /></label>)}<div className="flex items-end"><Button type="button" variant="ghost" onClick={() => removeRow(kind, index)}>Remove</Button></div></div>)}</div>)}
    {save.error && <p className="text-sm text-rose-600">{save.error.message}</p>}{save.isSuccess && <p className="text-sm text-emerald-600">Profile updated and audited.</p>}
    <Button disabled={save.isPending}>{save.isPending ? "Saving…" : "Save profile"}</Button>
  </form></Card>;
}
