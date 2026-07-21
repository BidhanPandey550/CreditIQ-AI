import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Badge, Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";

interface APIKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

interface CreatedAPIKey extends APIKey { key: string }

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";

export default function Integrations() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [expiry, setExpiry] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [revealedKey, setRevealedKey] = useState<string | null>(null);

  const keys = useQuery({ queryKey: ["api-keys"], queryFn: () => api.get<APIKey[]>("/integrations/api-keys") });
  const permissions = useQuery({ queryKey: ["api-key-scopes"], queryFn: () => api.get<Record<string, string>>("/integrations/api-key-scopes") });
  const createKey = useMutation({
    mutationFn: () => api.post<CreatedAPIKey>("/integrations/api-keys", {
      name,
      scopes: selectedScopes,
      expires_at: expiry ? new Date(expiry).toISOString() : null,
    }),
    onSuccess: (created) => {
      setRevealedKey(created.key);
      setName("");
      setExpiry("");
      setSelectedScopes([]);
      void queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
  const revokeKey = useMutation({
    mutationFn: (id: string) => api.post<APIKey>(`/integrations/api-keys/${id}/revoke`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  function toggleScope(scope: string) {
    setSelectedScopes((current) =>
      current.includes(scope) ? current.filter((item) => item !== scope) : [...current, scope],
    );
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setRevealedKey(null);
    createKey.mutate();
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">API key management</h1>
        <p className="mt-1 text-sm text-slate-500">Create scoped credentials for future connectors. No external banking integration is enabled by this screen.</p>
      </div>

      {revealedKey && <Card className="border-amber-300 bg-amber-50 dark:bg-amber-950/30"><h2 className="font-semibold text-amber-900 dark:text-amber-200">Copy this key now</h2><p className="mt-1 text-sm text-amber-800 dark:text-amber-300">For security, the secret is stored only as a hash and cannot be shown again.</p><code className="mt-3 block overflow-x-auto rounded-lg bg-slate-950 p-3 text-sm text-emerald-300">{revealedKey}</code><Button className="mt-3" variant="ghost" onClick={() => void navigator.clipboard.writeText(revealedKey)}>Copy key</Button></Card>}

      <Card>
        <h2 className="mb-4 font-semibold">Create API key</h2>
        <form className="space-y-4" onSubmit={submit}>
          <div className="grid gap-4 md:grid-cols-2"><label className="text-sm">Key name<input className={`${inputClass} mt-1`} required minLength={2} value={name} onChange={(event) => setName(event.target.value)} /></label><label className="text-sm">Expires at (optional)<input className={`${inputClass} mt-1`} type="datetime-local" value={expiry} onChange={(event) => setExpiry(event.target.value)} /></label></div>
          <fieldset><legend className="mb-2 text-sm font-medium">Permission scopes</legend><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(permissions.data ?? {}).map(([scope, description]) => <label key={scope} className="flex gap-2 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800"><input type="checkbox" checked={selectedScopes.includes(scope)} onChange={() => toggleScope(scope)} /><span><span className="block font-medium">{scope}</span><span className="text-xs text-slate-500">{description}</span></span></label>)}</div></fieldset>
          <Button disabled={createKey.isPending || selectedScopes.length === 0}>{createKey.isPending ? "Creating…" : "Create key"}</Button>
          {createKey.error && <p className="text-sm text-rose-600">{createKey.error.message}</p>}
        </form>
      </Card>

      <Card className="overflow-x-auto p-0"><table className="w-full text-sm"><thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800"><tr><th className="px-4 py-3">Key</th><th className="px-4 py-3">Scopes</th><th className="px-4 py-3">Expires</th><th className="px-4 py-3">Status</th><th className="px-4 py-3"></th></tr></thead><tbody>{keys.isLoading && <tr><td className="px-4 py-4 text-slate-500" colSpan={5}>Loading…</td></tr>}{keys.data?.map((key) => { const expired = !!key.expires_at && new Date(key.expires_at) <= new Date(); const status = key.revoked_at ? "Revoked" : expired ? "Expired" : "Active"; return <tr key={key.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800"><td className="px-4 py-3"><div className="font-medium">{key.name}</div><code className="text-xs text-slate-500">ciq_live_{key.prefix}…</code></td><td className="max-w-sm px-4 py-3 text-xs">{key.scopes.join(", ")}</td><td className="px-4 py-3">{key.expires_at ? new Date(key.expires_at).toLocaleString() : "Never"}</td><td className="px-4 py-3"><Badge label={status} /></td><td className="px-4 py-3">{!key.revoked_at && !expired && <Button variant="ghost" disabled={revokeKey.isPending} onClick={() => revokeKey.mutate(key.id)}>Revoke</Button>}</td></tr>; })}</tbody></table></Card>
    </div>
  );
}
