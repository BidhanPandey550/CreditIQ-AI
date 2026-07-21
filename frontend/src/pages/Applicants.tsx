import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Applicant {
  id: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  is_self_employed: boolean;
}

export default function Applicants() {
  const { can } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: ["applicants"],
    queryFn: () => api.get<Applicant[]>("/applicants"),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Applicants</h1>
        {can("applicant:manage") && (
          <Link to="/applicants/new">
            <Button>New Applicant</Button>
          </Link>
        )}
      </div>
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Phone</th>
              <th className="px-4 py-3">Employment</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td className="px-4 py-4 text-slate-500" colSpan={3}>
                  Loading…
                </td>
              </tr>
            )}
            {data?.map((a) => (
              <tr
                key={a.id}
                className="border-b border-slate-100 last:border-0 dark:border-slate-800"
              >
                <td className="px-4 py-3 font-medium">{a.full_name}</td>
                <td className="px-4 py-3">{a.phone ?? "—"}</td>
                <td className="px-4 py-3">{a.is_self_employed ? "Self-employed" : "Salaried"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
