import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, Flame, Target, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/MetricCard";
import { DashboardSkeleton } from "@/components/DashboardSection";
import { useActiveProfileId, useAuth } from "@/hooks/useAuth";
import { label, money, percent } from "@/lib/utils";
import { api } from "@/services/api";
import { Input } from "@/components/ui/input";

function exerciseName(exercise: any) {
  return exercise.name || exercise.exercise_name || "Exercise";
}

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
  const needsSetup = !data.user.phone || !data.user.email;
  return (
    <div className="grid gap-6">
      <header className="rounded-lg border bg-white p-6 shadow-soft">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Today</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Ready, {data.user.name}</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          {data.current_workout_plan?.title || "Your plan is waiting."} Keep the next session simple, honest, and logged.
        </p>
      </header>
      {needsSetup ? (
        <Card>
          <CardContent className="flex flex-col gap-3 pt-5 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 text-amber-600" size={18} />
              <div>
                <p className="font-medium">Complete your profile</p>
                <p className="text-sm text-muted-foreground">Add contact and body details so your gym can approve the right plan and follow up safely.</p>
              </div>
            </div>
            <Button type="button" onClick={() => { window.location.href = "/app/onboarding"; }}>
              Complete setup
            </Button>
          </CardContent>
        </Card>
      ) : null}
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
                  {day.exercises?.slice(0, 3).map(exerciseName).join(", ")}
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
                    <p className="font-medium">{exerciseName(exercise)}</p>
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

export function MemberRequestsPage() {
  const auth = useAuth();
  const profileId = useActiveProfileId(auth.profile);
  const orgId = auth.profile?.organization_id;
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    request_type: "workout_change",
    title: "Workout change request",
    message: "",
  });
  const requests = useQuery({
    queryKey: ["member-requests", orgId],
    queryFn: () => api.memberRequests(orgId!),
    enabled: Boolean(orgId),
  });
  const mutation = useMutation({
    mutationFn: () =>
      api.createMemberRequest(orgId!, profileId!, {
        ...form,
        payload: { source: "member_app" },
      }),
    onSuccess: async () => {
      setForm({ request_type: "workout_change", title: "Workout change request", message: "" });
      await queryClient.invalidateQueries({ queryKey: ["member-requests", orgId] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!orgId || !profileId || !form.message.trim()) return;
    mutation.mutate();
  }

  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Requests</h1>
      <Card>
        <CardHeader>
          <CardTitle>Ask your gym team</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={submit}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="grid gap-2 text-sm font-medium">
                Request type
                <select className="h-10 rounded-md border bg-card px-3 text-sm outline-none ring-primary/20 transition focus:ring-4" value={form.request_type} onChange={(event) => setForm({ ...form, request_type: event.target.value })}>
                  <option value="workout_change">Workout change</option>
                  <option value="diet_change">Diet help</option>
                  <option value="goal_change">Goal change</option>
                  <option value="injury_report">Report pain or injury</option>
                  <option value="membership_pause">Pause or freeze membership</option>
                  <option value="trainer_review">Trainer review</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm font-medium">
                Title
                <Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required />
              </label>
            </div>
            <label className="grid gap-2 text-sm font-medium">
              Details
              <textarea className="min-h-28 rounded-md border bg-card px-3 py-2 text-sm outline-none ring-primary/20 transition focus:ring-4" value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} required placeholder="Tell your trainer what changed, what hurts, or what you need." />
            </label>
            {mutation.error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{mutation.error.message}</p> : null}
            <Button disabled={mutation.isPending} type="submit">{mutation.isPending ? "Sending..." : "Send request"}</Button>
          </form>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Request history</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          {(requests.data || []).map((request) => (
            <div className="rounded-md border p-3" key={request.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{request.title}</p>
                  <p className="text-sm text-muted-foreground">{label(request.request_type)} · {label(request.status)}</p>
                </div>
                <span className="text-xs text-muted-foreground">{new Date(request.created_at).toLocaleDateString()}</span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{request.message}</p>
              {request.resolution_note ? <p className="mt-2 rounded-md bg-muted/40 p-2 text-sm">{request.resolution_note}</p> : null}
            </div>
          ))}
          {requests.data?.length === 0 ? <p className="text-sm text-muted-foreground">No requests yet.</p> : null}
        </CardContent>
      </Card>
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
  return <MemberProfilePage />;
}

export function MemberProfilePage() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const profileId = useActiveProfileId(auth.profile);
  const [form, setForm] = useState({
    name: auth.profile?.name || "",
    phone: auth.profile?.phone || "",
    email: auth.profile?.email || auth.account?.email || "",
    age: 25,
    height_cm: auth.profile?.height_cm || 170,
    weight_kg: auth.profile?.weight_kg || 70,
    fitness_goal: auth.profile?.fitness_goal || "maintenance",
    diet_preference: "veg",
    budget_amount: 250,
    budget_period: "daily",
    location: "India",
    gym_type: auth.profile?.gym_type || "local_gym",
  });
  const mutation = useMutation({
    mutationFn: () => api.updateProfile(profileId!, form),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["auth"] });
      await queryClient.invalidateQueries({ queryKey: ["member-dashboard", profileId] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!profileId) return;
    mutation.mutate();
  }

  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Profile setup</h1>
      <Card>
        <CardHeader>
          <CardTitle>Your details</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={submit}>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Name" value={form.name} onChange={(value) => setForm({ ...form, name: value })} />
              <Field label="WhatsApp phone" value={form.phone} onChange={(value) => setForm({ ...form, phone: value })} />
              <Field label="Email" type="email" value={form.email} onChange={(value) => setForm({ ...form, email: value })} />
              <Field label="Location" value={form.location} onChange={(value) => setForm({ ...form, location: value })} />
              <Field label="Age" type="number" value={form.age} onChange={(value) => setForm({ ...form, age: Number(value) })} />
              <Field label="Height cm" type="number" value={form.height_cm} onChange={(value) => setForm({ ...form, height_cm: Number(value) })} />
              <Field label="Weight kg" type="number" value={form.weight_kg} onChange={(value) => setForm({ ...form, weight_kg: Number(value) })} />
              <Field label="Food budget" type="number" value={form.budget_amount} onChange={(value) => setForm({ ...form, budget_amount: Number(value) })} />
              <label className="grid gap-2 text-sm font-medium">
                Goal
                <select className="h-10 rounded-md border bg-card px-3 text-sm outline-none ring-primary/20 transition focus:ring-4" value={form.fitness_goal} onChange={(event) => setForm({ ...form, fitness_goal: event.target.value })}>
                  <option value="fat_loss">Fat loss</option>
                  <option value="muscle_gain">Muscle gain</option>
                  <option value="maintenance">Maintenance</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm font-medium">
                Diet preference
                <select className="h-10 rounded-md border bg-card px-3 text-sm outline-none ring-primary/20 transition focus:ring-4" value={form.diet_preference} onChange={(event) => setForm({ ...form, diet_preference: event.target.value })}>
                  <option value="veg">Veg</option>
                  <option value="non_veg">Non-veg</option>
                </select>
              </label>
            </div>
            {mutation.isSuccess ? <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">Profile updated.</p> : null}
            {mutation.error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{mutation.error.message}</p> : null}
            <Button disabled={mutation.isPending} type="submit">{mutation.isPending ? "Saving..." : "Save profile"}</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label: labelText, value, onChange, type = "text" }: { label: string; value: string | number; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="grid gap-2 text-sm font-medium">
      {labelText}
      <Input type={type} value={value} onChange={(event) => onChange(event.target.value)} required />
    </label>
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
