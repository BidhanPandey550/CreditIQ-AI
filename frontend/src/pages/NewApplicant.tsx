import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm font-medium">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

const input =
  "w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700";

export default function NewApplicant() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    full_name: "",
    phone: "",
    national_id: "",
    is_self_employed: false,
    monthly_income: 60000,
    monthly_expense: 30000,
    existing_debt: 0,
    existing_installment: 0,
    is_delinquent: false,
  });

  const set = (k: string, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const create = useMutation({
    mutationFn: () =>
      api.post<{ id: string }>("/applicants", {
        full_name: form.full_name,
        phone: form.phone || null,
        national_id: form.national_id || null,
        is_self_employed: form.is_self_employed,
        employment: form.is_self_employed
          ? null
          : { monthly_income: Number(form.monthly_income) },
        incomes: [{ source: form.is_self_employed ? "Business" : "Salary", amount: Number(form.monthly_income) }],
        expenses: [{ category: "Living", amount: Number(form.monthly_expense) }],
        existing_loans:
          Number(form.existing_debt) > 0
            ? [
                {
                  outstanding_amount: Number(form.existing_debt),
                  monthly_installment: Number(form.existing_installment),
                  is_delinquent: form.is_delinquent,
                },
              ]
            : [],
      }),
    onSuccess: async (a) => {
      // Populate simulated wallet transactions so behavioural features are available.
      await api.post(`/applicants/${a.id}/simulate-transactions`).catch(() => {});
      qc.invalidateQueries({ queryKey: ["applicants"] });
      navigate("/applicants");
    },
  });

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-xl font-semibold">New Applicant</h1>
      <Card>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name">
            <input className={input} value={form.full_name} onChange={(e) => set("full_name", e.target.value)} />
          </Field>
          <Field label="Phone">
            <input className={input} value={form.phone} onChange={(e) => set("phone", e.target.value)} />
          </Field>
          <Field label="National ID (citizenship no.)">
            <input className={input} value={form.national_id} onChange={(e) => set("national_id", e.target.value)} />
          </Field>
          <Field label="Employment type">
            <select
              className={input}
              value={form.is_self_employed ? "self" : "salaried"}
              onChange={(e) => set("is_self_employed", e.target.value === "self")}
            >
              <option value="salaried">Salaried</option>
              <option value="self">Self-employed</option>
            </select>
          </Field>
          <Field label="Monthly income (NPR)">
            <input type="number" className={input} value={form.monthly_income} onChange={(e) => set("monthly_income", e.target.value)} />
          </Field>
          <Field label="Monthly expenses (NPR)">
            <input type="number" className={input} value={form.monthly_expense} onChange={(e) => set("monthly_expense", e.target.value)} />
          </Field>
          <Field label="Existing debt outstanding (NPR)">
            <input type="number" className={input} value={form.existing_debt} onChange={(e) => set("existing_debt", e.target.value)} />
          </Field>
          <Field label="Existing monthly installment (NPR)">
            <input type="number" className={input} value={form.existing_installment} onChange={(e) => set("existing_installment", e.target.value)} />
          </Field>
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_delinquent} onChange={(e) => set("is_delinquent", e.target.checked)} />
          Existing loan is delinquent
        </label>

        {create.isError && <p className="mt-3 text-sm text-rose-600">{(create.error as Error).message}</p>}

        <div className="mt-5 flex gap-2">
          <Button onClick={() => create.mutate()} disabled={create.isPending || !form.full_name}>
            {create.isPending ? "Creating…" : "Create applicant"}
          </Button>
          <Button variant="ghost" onClick={() => navigate("/applicants")}>
            Cancel
          </Button>
        </div>
      </Card>
    </div>
  );
}
