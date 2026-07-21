import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Badge, Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";

interface User {
  id: string;
  email: string;
  full_name: string;
  status: string;
  roles: string[];
  branch_id: string | null;
  applicant_id: string | null;
}

interface Role { name: string }
interface Branch { id: string; name: string; code: string }
interface Applicant { id: string; full_name: string; email: string | null }

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";

export default function Users() {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("Loan Officer");
  const [branchId, setBranchId] = useState("");
  const [applicantId, setApplicantId] = useState("");

  const users = useQuery({ queryKey: ["users"], queryFn: () => api.get<User[]>("/users") });
  const roles = useQuery({ queryKey: ["assignable-roles"], queryFn: () => api.get<Role[]>("/users/roles") });
  const branches = useQuery({ queryKey: ["branches"], queryFn: () => api.get<Branch[]>("/organizations/branches") });
  const applicants = useQuery({ queryKey: ["applicants"], queryFn: () => api.get<Applicant[]>("/applicants") });

  const createUser = useMutation({
    mutationFn: () => api.post<User>("/users", {
      email,
      full_name: fullName,
      password,
      role_names: [role],
      branch_id: role === "Applicant" || !branchId ? null : branchId,
      applicant_id: role === "Applicant" && applicantId ? applicantId : null,
    }),
    onSuccess: () => {
      setFullName("");
      setEmail("");
      setPassword("");
      setApplicantId("");
      void queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    createUser.mutate();
  }

  const branchName = (id: string | null) =>
    branches.data?.find((branch) => branch.id === id)?.name ?? "All branches";
  const applicantName = (id: string | null) =>
    applicants.data?.find((applicant) => applicant.id === id)?.full_name;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">User administration</h1>
        <p className="mt-1 text-sm text-slate-500">Provision tenant users with explicit role, branch, and applicant ownership scope.</p>
      </div>

      <Card>
        <h2 className="mb-4 font-semibold">Create user</h2>
        <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" onSubmit={submit}>
          <label className="text-sm">Full name<input className={`${inputClass} mt-1`} required value={fullName} onChange={(e) => setFullName(e.target.value)} /></label>
          <label className="text-sm">Email<input className={`${inputClass} mt-1`} required type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label className="text-sm">Temporary password<input className={`${inputClass} mt-1`} required minLength={8} type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          <label className="text-sm">Role<select className={`${inputClass} mt-1`} value={role} onChange={(e) => setRole(e.target.value)}>{roles.data?.map((item) => <option key={item.name}>{item.name}</option>)}</select></label>
          {role === "Applicant" ? (
            <label className="text-sm">Applicant ownership<select className={`${inputClass} mt-1`} required value={applicantId} onChange={(e) => setApplicantId(e.target.value)}><option value="">Select applicant</option>{applicants.data?.map((item) => <option key={item.id} value={item.id}>{item.full_name}{item.email ? ` — ${item.email}` : ""}</option>)}</select></label>
          ) : (
            <label className="text-sm">Branch scope<select className={`${inputClass} mt-1`} value={branchId} onChange={(e) => setBranchId(e.target.value)}><option value="">Organization-wide</option>{branches.data?.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.code})</option>)}</select></label>
          )}
          <div className="flex items-end"><Button disabled={createUser.isPending}>{createUser.isPending ? "Creating…" : "Create user"}</Button></div>
        </form>
        {createUser.error && <p className="mt-3 text-sm text-rose-600">{createUser.error.message}</p>}
        {createUser.isSuccess && <p className="mt-3 text-sm text-emerald-600">User created successfully.</p>}
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800"><tr><th className="px-4 py-3">User</th><th className="px-4 py-3">Role</th><th className="px-4 py-3">Scope</th><th className="px-4 py-3">Status</th></tr></thead>
          <tbody>
            {users.isLoading && <tr><td className="px-4 py-4 text-slate-500" colSpan={4}>Loading…</td></tr>}
            {users.data?.map((user) => <tr key={user.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800"><td className="px-4 py-3"><div className="font-medium">{user.full_name}</div><div className="text-xs text-slate-500">{user.email}</div></td><td className="px-4 py-3">{user.roles.join(", ")}</td><td className="px-4 py-3">{applicantName(user.applicant_id) ?? branchName(user.branch_id)}</td><td className="px-4 py-3"><Badge label={user.status} /></td></tr>)}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
