import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { usePrimaryOrganization } from "@/hooks/useOrganization";
import { label, money, percent } from "@/lib/utils";
import { api } from "@/services/api";
import { EmptyState, PageHeader, PageLoading } from "./BusinessOverview";

function useBusinessData() {
  const org = usePrimaryOrganization();
  const dashboard = useQuery({
    queryKey: ["business-dashboard", org.organization?.id],
    queryFn: () => api.businessDashboard(org.organization!.id),
    enabled: Boolean(org.organization?.id),
  });
  return { org, dashboard };
}

export function RetentionPage() {
  const { org, dashboard } = useBusinessData();
  if (org.isLoading || dashboard.isLoading) return <PageLoading label="Loading retention intelligence..." />;
  if (!dashboard.data) return <EmptyState title="Retention unavailable" detail={dashboard.error?.message || "No retention data found."} />;
  return (
    <div className="grid gap-6">
      <PageHeader eyebrow="Retention intelligence" title="Renewal risk pipeline" subtitle="Prioritize members most likely to churn before the renewal date." />
      <Card>
        <CardHeader>
          <CardTitle>At-risk members</CardTitle>
          <span className="text-sm text-muted-foreground">{money(dashboard.data.renewal_forecast.revenue_at_risk)} revenue at risk</span>
        </CardHeader>
        <CardContent className="scroll-table">
          <table className="w-full text-left text-sm">
            <thead className="text-muted-foreground">
              <tr>
                <th className="py-2">Member</th>
                <th>Risk</th>
                <th>Membership</th>
                <th>Reasons</th>
                <th>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.data.at_risk_members.map((risk) => (
                <tr className="border-t" key={risk.member.id}>
                  <td className="py-3 font-medium">{risk.member.name}</td>
                  <td>
                    <Badge tone={risk.level === "high" || risk.level === "critical" ? "danger" : "warning"}>{Math.round(risk.score)} {label(risk.level)}</Badge>
                  </td>
                  <td>{risk.membership?.days_remaining ?? "n/a"} days</td>
                  <td>{risk.signals?.map((signal: any) => label(signal.code)).join(", ")}</td>
                  <td>{recommend(risk)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

export function TrainerPerformancePage() {
  const { dashboard } = useBusinessData();
  if (dashboard.isLoading) return <PageLoading label="Loading trainer performance..." />;
  if (!dashboard.data) return <EmptyState title="Trainer data unavailable" detail={dashboard.error?.message || "No trainer data found."} />;
  return (
    <div className="grid gap-6">
      <PageHeader eyebrow="Trainer performance" title="Compare coaching effectiveness" subtitle="Retention, adherence, approvals, and risk load by trainer." />
      <Card>
        <CardContent className="scroll-table pt-5">
          <table className="w-full text-left text-sm">
            <thead className="text-muted-foreground">
              <tr>
                <th className="py-2">Trainer</th>
                <th>Active clients</th>
                <th>Retention</th>
                <th>Adherence</th>
                <th>Goal success</th>
                <th>Inactive</th>
                <th>Overdue approvals</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.data.trainer_performance.map((trainer) => (
                <tr className="border-t" key={trainer.trainer_account_id}>
                  <td className="py-3 font-medium">{trainer.trainer_email || `Trainer ${trainer.trainer_account_id}`}</td>
                  <td>{trainer.active_client_count}</td>
                  <td>{percent(trainer.client_retention_rate)}</td>
                  <td>{percent(trainer.avg_client_adherence)}</td>
                  <td>{percent(trainer.goal_success_rate)}</td>
                  <td>{trainer.inactive_clients}</td>
                  <td>{trainer.overdue_approvals}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

export function DailyActionsPage() {
  const { org, dashboard } = useBusinessData();
  const approvals = useQuery({
    queryKey: ["trainer-approvals", org.organization?.id],
    queryFn: () => api.pendingApprovals(org.organization!.id),
    enabled: Boolean(org.organization?.id),
  });
  if (dashboard.isLoading || approvals.isLoading) return <PageLoading label="Loading daily operations..." />;
  if (!dashboard.data) return <EmptyState title="Actions unavailable" detail={dashboard.error?.message || "No action data found."} />;
  return (
    <div className="grid gap-6">
      <PageHeader eyebrow="Daily operations" title="What should staff act on today?" subtitle="A focused queue for renewals, inactivity, approvals, and stalled progress." />
      <PlanApprovalPanel organizationId={org.organization?.id} approvals={approvals.data || []} />
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {dashboard.data.daily_actions.actions.map((action) => (
          <Card key={`${action.workflow_type}-${action.member.id}-${action.title}`}>
            <CardContent className="pt-5">
              <div className="mb-3 flex items-center justify-between">
                <Badge tone={action.priority === "high" ? "danger" : "warning"}>{action.priority}</Badge>
                <span className="text-xs text-muted-foreground">{label(action.workflow_type)}</span>
              </div>
              <h3 className="font-semibold">{action.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{action.message}</p>
              <p className="mt-4 text-sm font-medium">{action.member.name}</p>
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}

function PlanApprovalPanel({ organizationId, approvals }: { organizationId?: number; approvals: any[] }) {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: ({ planId, status }: { planId: number; status: "trainer_approved" | "trainer_modified" }) =>
      api.reviewWorkoutPlan(organizationId!, planId, {
        status,
        trainer_notes: status === "trainer_approved" ? "Approved from daily operations." : "Marked modified from daily operations.",
      }),
    onSuccess: async () => {
      setMessage("Plan review saved.");
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["trainer-approvals", organizationId] });
      await queryClient.invalidateQueries({ queryKey: ["business-dashboard", organizationId] });
    },
    onError: (err) => {
      setMessage("");
      setError(err instanceof Error ? err.message : "Could not save plan review.");
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pending AI plan approvals</CardTitle>
        <span className="text-sm text-muted-foreground">{approvals.length} waiting</span>
      </CardHeader>
      <CardContent className="grid gap-3">
        {message ? <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p> : null}
        {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {!approvals.length ? <p className="text-sm text-muted-foreground">No AI plans are waiting for review.</p> : null}
        {approvals.slice(0, 5).map((plan) => (
          <div className="grid gap-3 rounded-md border p-3 lg:grid-cols-[1fr_auto]" key={plan.plan_id}>
            <div>
              <p className="font-medium">{plan.member.name}</p>
              <p className="mt-1 text-sm text-muted-foreground">{plan.title} | {plan.week_start}</p>
              <p className="mt-2 text-sm text-muted-foreground">{plan.rationale || "No rationale provided."}</p>
            </div>
            <div className="flex flex-wrap items-start gap-2">
              <Button disabled={!organizationId || mutation.isPending} onClick={() => mutation.mutate({ planId: plan.plan_id, status: "trainer_approved" })}>
                Approve
              </Button>
              <Button disabled={!organizationId || mutation.isPending} variant="secondary" onClick={() => mutation.mutate({ planId: plan.plan_id, status: "trainer_modified" })}>
                Mark modified
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function TransformationPage() {
  const org = usePrimaryOrganization();
  const transformation = useQuery({
    queryKey: ["business-transformation", org.organization?.id],
    queryFn: () => api.businessTransformation(org.organization!.id),
    enabled: Boolean(org.organization?.id),
  });
  if (org.isLoading || transformation.isLoading) return <PageLoading label="Loading transformation outcomes..." />;
  if (!transformation.data) return <EmptyState title="Transformation unavailable" detail={transformation.error?.message || "No transformation data found."} />;
  return (
    <div className="grid gap-6">
      <PageHeader eyebrow="Transformation" title="Outcome proof" subtitle="Track body metrics, consistency, goal success, and transformation milestones." />
      <section className="metric-grid">
        <Stat label="Members tracked" value={transformation.data.members_tracked} />
        <Stat label="Body improvements" value={transformation.data.members_with_body_improvements} />
        <Stat label="Goal completion" value={`${transformation.data.goal_completion_pct}%`} />
        <Stat label="Milestones 90d" value={transformation.data.milestones_90d} />
      </section>
      <Card>
        <CardHeader>
          <CardTitle>Trainer transformation success</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          {transformation.data.trainer_success.map((trainer) => (
            <div className="grid gap-2 rounded-md border p-3 md:grid-cols-5" key={trainer.trainer_account_id}>
              <strong>Trainer {trainer.trainer_account_id}</strong>
              <span>{trainer.active_clients} clients</span>
              <span>{trainer.clients_with_improvements} improving</span>
              <span>{percent(trainer.goal_success_rate)} goals</span>
              <span>{trainer.milestones_90d} milestones</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label: labelText, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-sm text-muted-foreground">{labelText}</p>
        <strong className="mt-2 block text-3xl font-semibold">{value}</strong>
      </CardContent>
    </Card>
  );
}

function recommend(risk: any) {
  const codes = new Set((risk.signals || []).map((signal: any) => signal.code));
  if (codes.has("expired_membership")) return "Call and close renewal decision.";
  if (codes.has("inactivity")) return "Trainer follow-up and attendance restart.";
  if (codes.has("goal_stagnation")) return "Review goals and set next milestone.";
  return "Keep warm with structured follow-up.";
}
