import { useQuery } from "@tanstack/react-query";
import { Activity, Flame, Target, Trophy } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/MetricCard";
import { DashboardSkeleton } from "@/components/DashboardSection";
import { useActiveProfileId, useAuth } from "@/hooks/useAuth";
import { label, money, percent } from "@/lib/utils";
import { api } from "@/services/api";

export function MemberDashboard() {
  const auth = useAuth();
  const profileId = useActiveProfileId(auth.profile);
  const dashboard = useQuery({
    queryKey: ["member-dashboard", profileId],
    queryFn: () => api.memberDashboard(profileId!),
    enabled: Boolean(profileId),
  });

  if (dashboard.isLoading) return <DashboardSkeleton />;
  if (!dashboard.data) return <div className="rounded-lg border bg-white p-6">No member profile found.</div>;

  const data = dashboard.data;
  return (
    <div className="grid gap-6">
      <header className="rounded-lg border bg-white p-6 shadow-soft">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Today</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Ready, {data.user.name}</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          {data.current_workout_plan?.title || "Your plan is waiting."} Keep the next session simple, honest, and logged.
        </p>
      </header>
      <section className="metric-grid">
        <MetricCard label="Week completion" value={percent(data.progress.completion_rate)} detail={`${data.progress.current_week_completed}/${data.progress.current_week_planned} planned`} />
        <MetricCard label="Training logs" value={data.progress.total_logs} detail="All-time logged entries" />
        <MetricCard label="Calories" value={data.current_diet_plan?.calories || 0} detail={`${data.current_diet_plan?.protein_g || 0}g protein`} />
        <MetricCard label="Food budget" value={money(data.current_diet_plan?.estimated_daily_cost)} detail="Estimated daily cost" />
      </section>
      <section className="grid gap-6 lg:grid-cols-[1fr_0.85fr]">
        <Card>
          <CardHeader>
            <CardTitle>Next workout</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {(data.current_workout_plan?.days || []).slice(0, 3).map((day: any) => (
              <div className="rounded-md border bg-muted/30 p-3" key={day.day}>
                <div className="flex items-center justify-between">
                  <strong>{day.day}: {day.focus}</strong>
                  <span className="text-xs text-muted-foreground">{day.exercises?.length || 0} exercises</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {day.exercises?.slice(0, 3).map((exercise: any) => exercise.exercise_name).join(", ")}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Transformation signals</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Signal icon={Flame} label="Consistency" value={percent(data.progress.completion_rate)} />
            <Signal icon={Activity} label="Recent logs" value={`${data.progress.recent_logs?.length || 0} entries`} />
            <Signal icon={Target} label="Goal" value={label(data.user.fitness_goal)} />
            <Signal icon={Trophy} label="Review" value={data.weekly_summary ? "Updated" : "Pending"} />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

export function WorkoutPage() {
  const auth = useAuth();
  const profileId = useActiveProfileId(auth.profile);
  const dashboard = useQuery({ queryKey: ["member-dashboard", profileId], queryFn: () => api.memberDashboard(profileId!), enabled: Boolean(profileId) });
  const plan = dashboard.data?.current_workout_plan;
  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Workout session</h1>
      <section className="grid gap-4">
        {(plan?.days || []).map((day: any) => (
          <Card key={day.day}>
            <CardHeader>
              <CardTitle>{day.day}: {day.focus}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              {day.exercises?.map((exercise: any) => (
                <div className="flex items-center justify-between rounded-md border p-3" key={exercise.id || exercise.exercise_name}>
                  <div>
                    <p className="font-medium">{exercise.exercise_name}</p>
                    <p className="text-sm text-muted-foreground">{exercise.sets} sets | {exercise.target_reps} | {exercise.equipment}</p>
                  </div>
                  <span className="text-sm text-muted-foreground">{label(exercise.status || "pending")}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}

export function ProgressPage() {
  const auth = useAuth();
  const profileId = useActiveProfileId(auth.profile);
  const dashboard = useQuery({ queryKey: ["member-dashboard", profileId], queryFn: () => api.memberDashboard(profileId!), enabled: Boolean(profileId) });
  const logs = dashboard.data?.progress.recent_logs || [];
  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Progress</h1>
      <Card>
        <CardHeader>
          <CardTitle>Recent training</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          {logs.map((log: any, index: number) => (
            <div className="grid gap-2 rounded-md border p-3 md:grid-cols-4" key={`${log.exercise}-${log.date}-${index}`}>
              <strong>{log.exercise}</strong>
              <span>{log.date}</span>
              <span>{log.sets} sets x {log.reps}</span>
              <span>{log.weight_kg} kg</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export function GoalsPage() {
  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Goals</h1>
      <Card>
        <CardContent className="pt-5">
          <p className="text-muted-foreground">Goal tracking will move here from the legacy member dashboard in the next migration slice.</p>
        </CardContent>
      </Card>
    </div>
  );
}

function Signal({ icon: Icon, label: labelText, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-md border p-3">
      <Icon className="text-primary" size={18} />
      <div>
        <p className="text-sm text-muted-foreground">{labelText}</p>
        <p className="font-medium">{value}</p>
      </div>
    </div>
  );
}
