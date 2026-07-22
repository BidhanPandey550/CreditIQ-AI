import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Badge, Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";

export interface LoanProduct {
  id: string;
  code: string;
  name: string;
  min_amount: number;
  max_amount: number;
  min_tenor_months: number;
  max_tenor_months: number;
  interest_rate: number;
  status: string;
}

const input = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";

export default function LoanProducts() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ code: "", name: "", min_amount: 50000, max_amount: 1000000, min_tenor_months: 3, max_tenor_months: 60, interest_rate: 12 });
  const products = useQuery({ queryKey: ["loan-products", "all"], queryFn: () => api.get<LoanProduct[]>("/loan-products?include_inactive=true") });
  const create = useMutation({
    mutationFn: () => api.post<LoanProduct>("/loan-products", form),
    onSuccess: () => {
      setForm((current) => ({ ...current, code: "", name: "" }));
      void queryClient.invalidateQueries({ queryKey: ["loan-products"] });
    },
  });
  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.patch<LoanProduct>(`/loan-products/${id}`, { status }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["loan-products"] }),
  });
  const set = (name: string, value: string | number) => setForm((current) => ({ ...current, [name]: value }));

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return <div className="space-y-5">
    <div><h1 className="text-xl font-semibold">Loan products</h1><p className="mt-1 text-sm text-slate-500">Configure institution-owned amount, tenor, and pricing policies.</p></div>
    <Card><h2 className="mb-4 font-semibold">Create product</h2><form className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={submit}>
      <label className="text-sm">Code<input className={input} required pattern="[A-Za-z0-9][A-Za-z0-9_-]*" value={form.code} onChange={(event) => set("code", event.target.value)} /></label>
      <label className="text-sm">Name<input className={input} required value={form.name} onChange={(event) => set("name", event.target.value)} /></label>
      <label className="text-sm">Minimum amount<input className={input} type="number" min="1" required value={form.min_amount} onChange={(event) => set("min_amount", Number(event.target.value))} /></label>
      <label className="text-sm">Maximum amount<input className={input} type="number" min="1" required value={form.max_amount} onChange={(event) => set("max_amount", Number(event.target.value))} /></label>
      <label className="text-sm">Minimum tenor<input className={input} type="number" min="1" max="360" required value={form.min_tenor_months} onChange={(event) => set("min_tenor_months", Number(event.target.value))} /></label>
      <label className="text-sm">Maximum tenor<input className={input} type="number" min="1" max="360" required value={form.max_tenor_months} onChange={(event) => set("max_tenor_months", Number(event.target.value))} /></label>
      <label className="text-sm">Annual interest (%)<input className={input} type="number" min="0" max="100" step="0.001" required value={form.interest_rate} onChange={(event) => set("interest_rate", Number(event.target.value))} /></label>
      <div className="flex items-end"><Button disabled={create.isPending}>{create.isPending ? "Creating…" : "Create product"}</Button></div>
    </form>{create.error && <p className="mt-3 text-sm text-rose-600">{create.error.message}</p>}</Card>
    <Card className="overflow-x-auto p-0"><table className="w-full text-sm"><thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800"><tr><th className="px-4 py-3">Product</th><th className="px-4 py-3">Amount range</th><th className="px-4 py-3">Tenor</th><th className="px-4 py-3">Rate</th><th className="px-4 py-3">Status</th><th className="px-4 py-3"></th></tr></thead><tbody>
      {products.data?.map((product) => <tr key={product.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800"><td className="px-4 py-3"><div className="font-medium">{product.name}</div><div className="text-xs text-slate-500">{product.code}</div></td><td className="px-4 py-3">NPR {product.min_amount.toLocaleString()}–{product.max_amount.toLocaleString()}</td><td className="px-4 py-3">{product.min_tenor_months}–{product.max_tenor_months} months</td><td className="px-4 py-3">{product.interest_rate}%</td><td className="px-4 py-3"><Badge label={product.status} /></td><td className="px-4 py-3"><Button variant="ghost" disabled={changeStatus.isPending} onClick={() => changeStatus.mutate({ id: product.id, status: product.status === "active" ? "inactive" : "active" })}>{product.status === "active" ? "Deactivate" : "Activate"}</Button></td></tr>)}
    </tbody></table></Card>
  </div>;
}
