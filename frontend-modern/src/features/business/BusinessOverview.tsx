import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/MetricCard";
import { DashboardSkeleton } from "@/components/DashboardSection";
import { usePrimaryOrganization } from "@/hooks/useOrganization";
import { label, money, percent } from "@/lib/utils";
import { api } from "@/services/api";

export function BusinessOverview() {
  const org = usePrimaryOrganization();
  const dashboard = useQuery({
    queryKey: ["business-dashboard", org.organization?.id],
    queryFn: () => api.businessDashboard(org.organization!.id),
    enabled: Boolean(org.organization?.id),
  });

  if (org.isLoading || dashboard.isLoading) return <DashboardSkeleton />;
  if (!org.organization) return <EmptyState title="No organization found" detail="This account is not attached to a gym workspace yet." />;
  if (dashboard.error) return <EmptyState title="Business dashboard unavailable" detail={dashboard.error.message} />;

  const data = dashboard.data!;
  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Business overview"
        title={org.organization.name}
        subtitle="Revenue, retention, trainer performance, and daily operations."
      />
      <section className="metric-grid">
        <MetricCard label="Monthly revenue" value={money(data.revenue.monthly_recurring_revenue)} detail="Active membership run-rate" />
        <MetricCard label="Active memberships" value={data.revenue.active_memberships} detail="Current paying base" />
        <MetricCard label="Expiring soon" value={data.revenue.expiring_memberships_30d} detail="Renewals due in 30 days" />
        <MetricCard label="Revenue at risk" value={money(data.renewal_forecast.revenue_at_risk)} detail={`${data.renewal_forecast.high_risk_renewals} high-risk renewals`} />
      </section>
      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Daily follow-up actions</CardTitle>
            <span className="text-sm text-muted-foreground">{data.daily_actions.actions.length} open</span>
          </CardHeader>
          <CardContent className="grid gap-3">
            {data.daily_actions.actions.slice(0, 6).map((action) => (
              <div className="rounded-md border bg-muted/30 p-3" key={`${action.workflow_type}-${action.member.id}-${action.title}`}>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <Badge tone={action.priority === "high" ? "danger" : "warning"}>{action.priority}</Badge>
                  <span className="text-xs text-muted-foreground">{label(action.workflow_type)}</span>
                </div>
                <p className="font-medium">{action.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{action.message}</p>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Renewal intelligence</CardTitle>
            <span className="text-sm text-muted-foreground">{percent(data.renewal_forecast.renewal_probability)} expected renewal rate</span>
          </CardHeader>
          <CardContent className="grid gap-3">
            {data.at_risk_members.slice(0, 6).map((risk) => (
              <div className="flex items-start justify-between gap-4 rounded-md border p-3" key={risk.member.id}>
                <div>
                  <p className="font-medium">{risk.member.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{risk.signals?.slice(0, 2).map((signal: any) => label(signal.code)).join(", ")}</p>
                </div>
                <Badge tone={risk.level === "critical" || risk.level === "high" ? "danger" : "warning"}>{Math.round(risk.score)}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
      <section className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Trainer performance</CardTitle>
          </CardHeader>
          <CardContent className="scroll-table">
            <table className="w-full text-left text-sm">
              <thead className="text-muted-foreground">
                <tr>
                  <th className="py-2">Trainer</th>
                  <th>Clients</th>
                  <th>Retention</th>
                  <th>Adherence</th>
                  <th>Risks</th>
                </tr>
              </thead>
              <tbody>
                {data.trainer_performance.map((trainer) => (
                  <tr className="border-t" key={trainer.trainer_account_id}>
                    <td className="py-3 font-medium">{trainer.trainer_email || `Trainer ${trainer.trainer_account_id}`}</td>
                    <td>{trainer.active_client_count}</td>
                    <td>{percent(trainer.client_retention_rate)}</td>
                    <td>{percent(trainer.avg_client_adherence)}</td>
                    <td>{trainer.high_risk_clients} high-risk</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Operating health</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <HealthRow ok={data.revenue.unpaid_members.length === 0} label="Collections" detail={`${data.revenue.unpaid_members.length} unpaid members`} />
            <HealthRow ok={data.renewal_forecast.high_risk_renewals === 0} label="Renewals" detail={`${data.renewal_forecast.high_risk_renewals} high-risk renewals`} />
            <HealthRow ok={data.daily_actions.actions.length < 5} label="Action load" detail={`${data.daily_actions.actions.length} staff tasks`} />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function HealthRow({ ok, label: labelText, detail }: { ok: boolean; label: string; detail: string }) {
  return (
    <div className="flex items-center gap-3 rounded-md border p-3">
      {ok ? <CheckCircle2 className="text-emerald-600" size={18} /> : <AlertTriangle className="text-amber-600" size={18} />}
      <div>
        <p className="font-medium">{labelText}</p>
        <p className="text-sm text-muted-foreground">{detail}</p>
      </div>
    </div>
  );
}

export function PageHeader({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle: string }) {
  return (
    <header>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{eyebrow}</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">{title}</h1>
      <p className="mt-2 max-w-3xl text-muted-foreground">{subtitle}</p>
    </header>
  );
}

export function PageLoading({ label: text }: { label: string }) {
  return <DashboardSkeleton />;
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <h2 className="text-xl font-semibold">{title}</h2>
        <p className="mt-2 text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}
