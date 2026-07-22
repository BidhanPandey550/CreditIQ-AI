import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface OrganizationSummary {
  id: string;
  name: string;
  type: string;
  status: string;
  nrb_license_no: string | null;
  created_at: string;
}

export default function OrganizationSwitcher() {
  const { me, can, switchOrganization } = useAuth();
  const [switching, setSwitching] = useState(false);
  const organizations = useQuery({
    queryKey: ["platform-organizations"],
    queryFn: () => api.get<OrganizationSummary[]>("/organizations"),
    enabled: can("platform:admin"),
  });

  if (!can("platform:admin") || !me) return null;

  return (
    <label className="flex items-center gap-2 text-xs text-slate-500">
      <span className="hidden lg:inline">Organization</span>
      <select
        aria-label="Active organization"
        className="max-w-52 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
        disabled={switching || organizations.isLoading}
        value={me.organization_id}
        onChange={async (event) => {
          setSwitching(true);
          try {
            await switchOrganization(event.target.value);
          } finally {
            setSwitching(false);
          }
        }}
      >
        {organizations.data?.map((organization) => (
          <option key={organization.id} value={organization.id} disabled={organization.status !== "active"}>
            {organization.name}{organization.id === me.home_organization_id ? " (home)" : ""}{organization.status !== "active" ? ` — ${organization.status}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
