import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";

interface Applicant {
  id: string;
  full_name: string;
}

const input =
  "w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700";

export default function NewLoan() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: applicants } = useQuery({
    queryKey: ["applicants"],
    queryFn: () => api.get<Applicant[]>("/applicants"),
  });

  const [form, setForm] = useState({ applicant_id: "", amount: 300000, tenor_months: 24, purpose: "" });
  const set = (k: string, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const create = useMutation({
    mutationFn: () =>
      api.post<{ id: string }>("/loans", {
        applicant_id: form.applicant_id,
        amount: Number(form.amount),
        tenor_months: Number(form.tenor_months),
        purpose: form.purpose || null,
      }),
    onSuccess: (loan) => {
      qc.invalidateQueries({ queryKey: ["loans"] });
      navigate(`/loans/${loan.id}`);
    },
  });

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-xl font-semibold">New Loan Application</h1>
      <Card>
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium">Applicant</span>
            <select
              className={`mt-1 ${input}`}
              value={form.applicant_id}
              onChange={(e) => set("applicant_id", e.target.value)}
            >
              <option value="">Select an applicant…</option>
              {applicants?.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.full_name}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm font-medium">Amount (NPR)</span>
              <input type="number" className={`mt-1 ${input}`} value={form.amount} onChange={(e) => set("amount", e.target.value)} />
            </label>
            <label className="block">
              <span className="text-sm font-medium">Tenor (months)</span>
              <input type="number" className={`mt-1 ${input}`} value={form.tenor_months} onChange={(e) => set("tenor_months", e.target.value)} />
            </label>
          </div>
          <label className="block">
            <span className="text-sm font-medium">Purpose</span>
            <input className={`mt-1 ${input}`} value={form.purpose} onChange={(e) => set("purpose", e.target.value)} />
          </label>
        </div>

        {create.isError && <p className="mt-3 text-sm text-rose-600">{(create.error as Error).message}</p>}

        <div className="mt-5 flex gap-2">
          <Button onClick={() => create.mutate()} disabled={create.isPending || !form.applicant_id}>
            {create.isPending ? "Creating…" : "Create application"}
          </Button>
          <Button variant="ghost" onClick={() => navigate("/loans")}>
            Cancel
          </Button>
        </div>
        <p className="mt-3 text-xs text-slate-400">
          Created as a draft. Open it to submit, run AI analysis, and record a decision.
        </p>
      </Card>
    </div>
  );
}
