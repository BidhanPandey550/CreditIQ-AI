import { useState } from "react";
import { Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function Reports() {
  const { can } = useAuth();
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function exportLoans() {
    setExporting(true);
    setError(null);
    try {
      const date = new Date().toISOString().slice(0, 10);
      await api.download("/reports/loans.csv", `creditiq-loans-${date}.csv`);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setExporting(false);
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
              CSV containing applications, latest risk assessment, default probability, and credit
              score. The export is restricted to your organization.
            </p>
          </div>
          {can("report:export") ? (
            <Button onClick={exportLoans} disabled={exporting}>
              {exporting ? "Preparing…" : "Download CSV"}
            </Button>
          ) : (
            <span className="text-sm text-amber-600">Export permission required</span>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </Card>
      <Card className="max-w-2xl border-dashed">
        <h2 className="font-medium">PDF regulatory packs</h2>
        <p className="mt-1 text-sm text-slate-500">
          Planned for the production reporting phase after document templates and NRB retention
          requirements are approved. This interface does not claim PDF support before it exists.
        </p>
      </Card>
    </div>
  );
}
