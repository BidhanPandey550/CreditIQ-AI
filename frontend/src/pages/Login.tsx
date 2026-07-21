import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card } from "../components/ui/primitives";
import { useAuth } from "../lib/auth";

export default function Login() {
  const { login, verifyMfa } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("officer@himalayan-demo.com");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [challenge, setChallenge] = useState<string | null>(null);
  const [code, setCode] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (challenge) {
        await verifyMfa(challenge, code);
      } else {
        const nextChallenge = await login(email, password);
        if (nextChallenge) {
          setChallenge(nextChallenge);
          return;
        }
      }
      navigate("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center p-4">
      <Card className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-brand font-bold text-white">
            IQ
          </div>
          <div>
            <div className="font-semibold">CreditIQ AI</div>
            <div className="text-xs text-slate-500">Credit Intelligence Platform</div>
          </div>
        </div>
        <form onSubmit={submit} className="space-y-3">
          {challenge ? (
            <div>
              <label className="text-sm font-medium">Authenticator code</label>
              <input
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-center font-mono text-lg tracking-[0.35em] dark:border-slate-700"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                autoFocus
              />
              <p className="mt-2 text-xs text-slate-500">Enter the current six-digit code from your authenticator app.</p>
            </div>
          ) : (
            <>
              <div>
                <label className="text-sm font-medium">Email</label>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Password</label>
                <input
                  type="password"
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </>
          )}
          {error && <div className="text-sm text-rose-600">{error}</div>}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Verifying…" : challenge ? "Verify code" : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-xs text-slate-400">
          Demo: officer@himalayan-demo.com · analyst@himalayan-demo.com · admin@himalayan-demo.com
          — password <code>ChangeMe123!</code>
        </p>
      </Card>
    </div>
  );
}
