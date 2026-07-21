import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";

interface Enrollment {
  secret: string;
  provisioning_uri: string;
}

export default function Security() {
  const status = useQuery({
    queryKey: ["mfa-status"],
    queryFn: () => api.get<{ enabled: boolean }>("/auth/mfa/status"),
  });
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function begin() {
    setBusy(true);
    setMessage(null);
    try {
      setEnrollment(await api.post<Enrollment>("/auth/mfa/enroll"));
    } catch (cause) {
      setMessage((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    try {
      await api.post<void>("/auth/mfa/confirm", { code });
      setEnrollment(null);
      setCode("");
      setMessage("Multi-factor authentication is enabled.");
      await status.refetch();
    } catch (cause) {
      setMessage((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function disable() {
    setBusy(true);
    try {
      await api.post<void>("/auth/mfa/disable", { code });
      setCode("");
      setMessage("Multi-factor authentication is disabled.");
      await status.refetch();
    } catch (cause) {
      setMessage((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Account Security</h1>
        <p className="mt-1 text-sm text-slate-500">Protect your CreditIQ account with a time-based authenticator code.</p>
      </div>
      <Card className="max-w-2xl space-y-4">
        <div>
          <h2 className="font-medium">Authenticator MFA</h2>
          <p className="mt-1 text-sm text-slate-500">Status: {status.data?.enabled ? "Enabled" : "Not enabled"}</p>
        </div>
        {enrollment && (
          <div className="space-y-3 rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
            <p className="text-sm">Add this setup key to your authenticator app, then confirm the current code.</p>
            <code className="block break-all rounded bg-white p-3 text-sm dark:bg-slate-900">{enrollment.secret}</code>
            <details className="text-xs text-slate-500"><summary>Provisioning URI</summary><code className="break-all">{enrollment.provisioning_uri}</code></details>
          </div>
        )}
        {(enrollment || status.data?.enabled) && (
          <input
            aria-label="Authenticator code"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
            className="w-48 rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-center font-mono tracking-[0.3em] dark:border-slate-700"
            placeholder="000000"
          />
        )}
        <div>
          {status.data?.enabled ? (
            <Button variant="ghost" disabled={busy || code.length !== 6} onClick={disable}>Disable MFA</Button>
          ) : enrollment ? (
            <Button disabled={busy || code.length !== 6} onClick={confirm}>Confirm and enable</Button>
          ) : (
            <Button disabled={busy} onClick={begin}>Set up MFA</Button>
          )}
        </div>
        {message && <p className="text-sm text-slate-600 dark:text-slate-300">{message}</p>}
      </Card>
    </div>
  );
}
