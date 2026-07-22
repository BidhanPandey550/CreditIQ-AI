import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

const nav = [
  { to: "/", label: "Dashboard", permission: null },
  { to: "/loans", label: "Loans", permission: "loan:read" },
  { to: "/applicants", label: "Applicants", permission: "applicant:read" },
  { to: "/reports", label: "Reports", permission: "report:export" },
  { to: "/users", label: "Users", permission: "user:manage" },
  { to: "/integrations", label: "API Keys", permission: "org:configure" },
  { to: "/organization", label: "Organization", permission: "org:configure" },
  { to: "/notifications", label: "Notifications", permission: "notification:read" },
  { to: "/security", label: "Security", permission: null },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { me, logout, can } = useAuth();
  const navigate = useNavigate();
  const [dark, setDark] = useState(
    () => localStorage.getItem("theme") === "dark",
  );

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  const visibleNav = [
    ...nav,
    { to: "/audit", label: "Audit", permission: "audit:read" },
  ].filter((item) => item.permission === null || can(item.permission));

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 flex-col border-r border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 md:flex">
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-sm font-bold text-white">
            IQ
          </div>
          <span className="font-semibold">CreditIQ AI</span>
        </div>
        <nav className="flex flex-col gap-1">
          {visibleNav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive
                    ? "bg-brand/10 text-brand dark:text-brand-light"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 sm:px-6">
          <div className="text-sm text-slate-500 dark:text-slate-400">
            {me?.roles.join(", ")}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setDark(!dark)}
              className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
            >
              {dark ? "☀️" : "🌙"}
            </button>
            <span className="hidden text-sm font-medium sm:inline">{me?.full_name}</span>
            <button
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              className="text-sm text-slate-500 hover:text-brand"
            >
              Sign out
            </button>
          </div>
        </header>
        <nav className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-900 md:hidden">
          {visibleNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-brand/10 text-brand" : "text-slate-500"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
