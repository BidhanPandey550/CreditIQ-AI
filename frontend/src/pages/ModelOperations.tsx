import { useQuery } from "@tanstack/react-query";
import { Badge, Card, Stat } from "../components/ui/primitives";
import { api } from "../lib/api";

interface ModelOperationsStatus {
  model: {
    version: string;
    algorithm: string;
    features_used: number;
    metrics: Record<string, number>;
    stage: string;
    data_source: string;
    feature_version: string;
  };
  monitoring: {
    prediction_count: number;
    failure_count: number;
    failure_rate: number;
    average_latency_ms: number;
    p95_latency_ms: number;
    status: string;
    reasons: string[];
    generated_at: string;
  };
}

export default function ModelOperations() {
  const status = useQuery({
    queryKey: ["model-operations"],
    queryFn: () => api.get<ModelOperationsStatus>("/admin/model-operations"),
    refetchInterval: 30_000,
  });

  if (status.isLoading) return <p className="text-slate-500">Loading model operations…</p>;
  if (status.isError) return <p className="text-rose-600">{status.error.message}</p>;
  if (!status.data) return null;

  const { model, monitoring } = status.data;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Model Operations</h1>
          <p className="mt-1 text-sm text-slate-500">
            Governed serving identity and privacy-safe runtime health.
          </p>
        </div>
        <div className="flex gap-2"><Badge label={model.stage} /><Badge label={monitoring.status} /></div>
      </div>

      {model.stage !== "production" && (
        <Card className="border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
          <p className="text-sm text-amber-800 dark:text-amber-200">
            Development model active. Synthetic predictions must not be used for real lending decisions.
          </p>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Predictions" value={monitoring.prediction_count.toLocaleString()} />
        <Stat label="Failure rate" value={`${(monitoring.failure_rate * 100).toFixed(2)}%`} hint={`${monitoring.failure_count} failed`} />
        <Stat label="Average latency" value={`${monitoring.average_latency_ms.toFixed(1)} ms`} />
        <Stat label="P95 latency" value={`${monitoring.p95_latency_ms.toFixed(1)} ms`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="font-medium">Deployed model</h2>
          <dl className="mt-4 grid grid-cols-[9rem_1fr] gap-x-4 gap-y-3 text-sm">
            <dt className="text-slate-500">Version</dt><dd className="font-mono">{model.version}</dd>
            <dt className="text-slate-500">Algorithm</dt><dd>{model.algorithm.replace(/_/g, " ")}</dd>
            <dt className="text-slate-500">Feature schema</dt><dd className="font-mono">{model.feature_version}</dd>
            <dt className="text-slate-500">Features</dt><dd>{model.features_used}</dd>
            <dt className="text-slate-500">Dataset lineage</dt><dd>{model.data_source}</dd>
          </dl>
        </Card>
        <Card>
          <h2 className="font-medium">Validation metrics</h2>
          <div className="mt-4 space-y-3">
            {Object.entries(model.metrics).map(([name, value]) => (
              <div key={name} className="flex items-center justify-between border-b border-slate-100 pb-2 text-sm last:border-0 dark:border-slate-800">
                <span className="capitalize text-slate-500">{name.replace(/_/g, " ")}</span>
                <span className="font-medium">{typeof value === "number" ? value.toFixed(4) : value}</span>
              </div>
            ))}
            {Object.keys(model.metrics).length === 0 && <p className="text-sm text-slate-500">No metrics disclosed.</p>}
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="font-medium">Operational assessment</h2>
        <p className="mt-2 text-sm text-slate-500">
          Updated {new Date(monitoring.generated_at).toLocaleString()}. Telemetry contains no applicant identifiers or raw features.
        </p>
        {monitoring.reasons.length > 0 && (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-amber-700 dark:text-amber-300">
            {monitoring.reasons.map((reason) => <li key={reason}>{reason.replace(/_/g, " ")}</li>)}
          </ul>
        )}
      </Card>
    </div>
  );
}
