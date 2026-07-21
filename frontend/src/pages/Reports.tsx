import { useState } from "react";
import { Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function Reports() {
  const { can } = useAuth();
  const [exporting, setExporting] = useState<"csv" | "pdf" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function exportLoans(format: "csv" | "pdf") {
    setExporting(format);
    setError(null);
    try {
      const date = new Date().toISOString().slice(0, 10);
      await api.download(`/reports/loans.${format}`, `creditiq-loans-${date}.${format}`);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setExporting(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Reports & Exports</h1>
        <p className="mt-1 text-sm text-slate-500">
          Generate tenant-isolated portfolio files for analysis and audit workflows.
        </p>
      </div>
      <Card className="max-w-2xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-medium">Loan portfolio export</h2>
            <p className="mt-1 text-sm text-slate-500">
              Export applications, latest risk assessment, default probability, and credit score.
              Every file is restricted to your organization and authorized branch scope.
            </p>
          </div>
          {can("report:export") ? (
            <div className="flex gap-2">
              <Button onClick={() => exportLoans("csv")} disabled={exporting !== null}>
                {exporting === "csv" ? "Preparing…" : "Download CSV"}
              </Button>
              <Button onClick={() => exportLoans("pdf")} disabled={exporting !== null}>
                {exporting === "pdf" ? "Preparing…" : "Download PDF"}
              </Button>
            </div>
          ) : (
            <span className="text-sm text-amber-600">Export permission required</span>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </Card>
    </div>
  );
}
