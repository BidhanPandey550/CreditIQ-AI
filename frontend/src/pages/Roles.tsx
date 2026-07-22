import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Badge, Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Role { id: string | null; name: string; is_system: boolean; permissions: string[] }

export default function Roles() {
  const queryClient = useQueryClient();
  const { me } = useAuth();
  const roles = useQuery({ queryKey: ["roles"], queryFn: () => api.get<Role[]>("/roles") });
  const catalog = useQuery({ queryKey: ["permission-catalog"], queryFn: () => api.get<Record<string, string>>("/users/permissions") });
  const [selected, setSelected] = useState<Role | null>(null);
  const [name, setName] = useState("");
  const [permissions, setPermissions] = useState<string[]>([]);
  useEffect(() => { setName(selected?.name ?? ""); setPermissions(selected?.permissions ?? []); }, [selected]);
  const available = Object.entries(catalog.data ?? {}).filter(([code]) => me?.permissions.includes("platform:admin") || me?.permissions.includes(code));
  const mutation = useMutation({
    mutationFn: () => selected?.id
      ? api.patch<Role>(`/roles/${selected.id}`, { name, permissions })
      : api.post<Role>("/roles", { name, permissions }),
    onSuccess: () => {
      setSelected(null); setName(""); setPermissions([]);
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
      void queryClient.invalidateQueries({ queryKey: ["assignable-roles"] });
    },
  });
  const toggle = (code: string) => setPermissions((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code]);
  const submit = (event: FormEvent) => { event.preventDefault(); mutation.mutate(); };

  return <div className="space-y-5">
    <div><h1 className="text-xl font-semibold">Roles and permissions</h1><p className="mt-1 text-sm text-slate-500">Compose least-privilege tenant roles. Platform system roles remain immutable.</p></div>
    <div className="grid gap-5 xl:grid-cols-[1fr_1.4fr]">
      <Card className="space-y-3"><h2 className="font-semibold">Role catalog</h2>{roles.data?.map((role) => <button className="flex w-full items-center justify-between rounded-lg border border-slate-200 p-3 text-left hover:border-brand dark:border-slate-800" key={role.name} onClick={() => !role.is_system && setSelected(role)}><span><span className="font-medium">{role.name}</span><span className="mt-1 block text-xs text-slate-500">{role.permissions.length} permissions</span></span><Badge label={role.is_system ? "system" : "custom"} /></button>)}</Card>
      <Card><form className="space-y-4" onSubmit={submit}><div><h2 className="font-semibold">{selected ? `Edit ${selected.name}` : "Create custom role"}</h2><p className="text-sm text-slate-500">Only permissions currently held by your account can be delegated.</p></div><label className="block text-sm">Role name<input className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950" minLength={2} maxLength={80} required value={name} onChange={(event) => setName(event.target.value)} /></label><div className="grid gap-2 md:grid-cols-2">{available.map(([code, description]) => <label className="flex gap-2 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800" key={code}><input type="checkbox" checked={permissions.includes(code)} onChange={() => toggle(code)} /><span><span className="font-medium">{code}</span><span className="block text-xs text-slate-500">{description}</span></span></label>)}</div>{mutation.error && <p className="text-sm text-rose-600">{mutation.error.message}</p>}<div className="flex gap-2"><Button disabled={mutation.isPending || !name || permissions.length === 0}>{mutation.isPending ? "Saving…" : selected ? "Update role" : "Create role"}</Button>{selected && <Button type="button" variant="ghost" onClick={() => setSelected(null)}>Cancel</Button>}</div></form></Card>
    </div>
  </div>;
}
