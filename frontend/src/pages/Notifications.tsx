import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card } from "../components/ui/primitives";
import { api } from "../lib/api";

interface Notification {
  id: string;
  channel: string;
  title: string;
  body: string | null;
  is_read: boolean;
  delivery_status: string;
  created_at: string;
}

export default function Notifications() {
  const queryClient = useQueryClient();
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<Notification[]>("/notifications"),
  });
  const markRead = useMutation({
    mutationFn: (id: string) => api.post<Notification>(`/notifications/${id}/read`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Notifications</h1>
        <p className="mt-1 text-sm text-slate-500">
          Operational alerts and review requests for your organization.
        </p>
      </div>
      {notifications.isLoading && <p className="text-sm text-slate-500">Loading alerts…</p>}
      {notifications.isError && (
        <p className="text-sm text-rose-600">{(notifications.error as Error).message}</p>
      )}
      {notifications.data?.length === 0 && (
        <Card><p className="text-sm text-slate-500">You have no notifications.</p></Card>
      )}
      <div className="space-y-3">
        {notifications.data?.map((item) => (
          <Card key={item.id} className={item.is_read ? "opacity-70" : "border-brand/40"}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-medium">{item.title}</h2>
                  {!item.is_read && <span className="h-2 w-2 rounded-full bg-brand" />}
                </div>
                {item.body && <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{item.body}</p>}
                <p className="mt-2 text-xs text-slate-400">
                  {new Date(item.created_at).toLocaleString()} · {item.channel.replace("_", " ")}
                </p>
              </div>
              {!item.is_read && (
                <Button
                  variant="ghost"
                  onClick={() => markRead.mutate(item.id)}
                  disabled={markRead.isPending}
                >
                  Mark as read
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>
      {markRead.isError && <p className="text-sm text-rose-600">{(markRead.error as Error).message}</p>}
    </div>
  );
}
