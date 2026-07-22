import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { Badge, Button, Card, Stat } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Applicant { id: string; full_name: string; phone: string | null; email: string | null }
interface Financials { monthly_income: number; monthly_expenses: number; debt_to_income: number; savings_ratio: number; net_worth: number }
interface Document { id: string; doc_type: string; original_filename: string | null; content_type: string | null; size_bytes: number | null; checksum: string | null; scan_status: string; created_at: string }

export default function ApplicantDetail() {
  const { id } = useParams();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [docType, setDocType] = useState("income_statement");
  const [file, setFile] = useState<File | null>(null);
  const applicant = useQuery({ queryKey: ["applicant", id], queryFn: () => api.get<Applicant>(`/applicants/${id}`) });
  const financials = useQuery({ queryKey: ["financials", id], queryFn: () => api.get<Financials>(`/applicants/${id}/financials`) });
  const documents = useQuery({ queryKey: ["documents", id], queryFn: () => api.get<Document[]>(`/applicants/${id}/documents`), enabled: can("document:read") });
  const upload = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Select a document first");
      const body = new FormData();
      body.append("doc_type", docType);
      body.append("file", file);
      return api.upload<Document>(`/applicants/${id}/documents`, body);
    },
    onSuccess: () => {
      setFile(null);
      void queryClient.invalidateQueries({ queryKey: ["documents", id] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    upload.mutate();
  }

  if (applicant.isLoading) return <p className="text-slate-500">Loading applicant…</p>;
  if (applicant.error) return <p className="text-rose-600">{applicant.error.message}</p>;

  return <div className="space-y-5">
    <div><h1 className="text-xl font-semibold">{applicant.data?.full_name}</h1><p className="text-sm text-slate-500">{applicant.data?.email ?? "No email"} · {applicant.data?.phone ?? "No phone"}</p></div>
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Stat label="Monthly income" value={`NPR ${(financials.data?.monthly_income ?? 0).toLocaleString()}`} /><Stat label="Monthly expenses" value={`NPR ${(financials.data?.monthly_expenses ?? 0).toLocaleString()}`} /><Stat label="Debt-to-income" value={`${((financials.data?.debt_to_income ?? 0) * 100).toFixed(1)}%`} /><Stat label="Net worth" value={`NPR ${(financials.data?.net_worth ?? 0).toLocaleString()}`} /></div>
    {can("document:upload") && <Card><h2 className="font-medium">Upload financial document</h2><p className="mt-1 text-sm text-slate-500">PDF, JPEG, or PNG only. Files are private, checksum-verified, and malware-screened when the scanner is available.</p><form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={submit}><label className="text-sm">Document type<select className="mt-1 block rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700" value={docType} onChange={(event) => setDocType(event.target.value)}><option value="income_statement">Income statement</option><option value="bank_statement">Bank statement</option><option value="identity_document">Identity document</option><option value="tax_document">Tax document</option><option value="other">Other</option></select></label><label className="text-sm">File<input className="mt-1 block text-sm" accept="application/pdf,image/jpeg,image/png" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label><Button disabled={!file || upload.isPending}>{upload.isPending ? "Uploading…" : "Upload"}</Button></form>{upload.error && <p className="mt-2 text-sm text-rose-600">{upload.error.message}</p>}</Card>}
    {can("document:read") && <Card className="overflow-x-auto p-0"><table className="w-full text-sm"><thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800"><tr><th className="px-4 py-3">Document</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Integrity</th><th className="px-4 py-3">Uploaded</th><th className="px-4 py-3"></th></tr></thead><tbody>{documents.data?.map((document) => <tr key={document.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800"><td className="px-4 py-3">{document.original_filename ?? "Document"}<div className="text-xs text-slate-500">{document.size_bytes ? `${(document.size_bytes / 1024).toFixed(1)} KB` : ""}</div></td><td className="px-4 py-3 capitalize">{document.doc_type.replace(/_/g, " ")}</td><td className="px-4 py-3"><Badge label={document.scan_status.replace(/_/g, " ")} /></td><td className="px-4 py-3">{new Date(document.created_at).toLocaleDateString()}</td><td className="px-4 py-3"><Button variant="ghost" onClick={() => api.download(`/applicants/${id}/documents/${document.id}/download`, document.original_filename ?? "document")}>Download</Button></td></tr>)}{documents.data?.length === 0 && <tr><td className="px-4 py-4 text-slate-500" colSpan={5}>No documents uploaded.</td></tr>}</tbody></table></Card>}
  </div>;
}
