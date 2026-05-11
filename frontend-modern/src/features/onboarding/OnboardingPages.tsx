import { FormEvent, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, Dumbbell, Mail, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useActiveProfileId, useAuth } from "@/hooks/useAuth";
import { usePrimaryOrganization } from "@/hooks/useOrganization";
import { api } from "@/services/api";

const businessSteps = [
  {
    title: "Create organization",
    detail: "Set up the gym profile, location, timezone, and operating contact.",
    done: true,
  },
  {
    title: "Create membership plans",
    detail: "Add monthly, quarterly, and annual plans so revenue dashboards have structure.",
    done: true,
  },
  {
    title: "Invite trainers",
    detail: "Bring coaching staff into the trainer workspace and assign client ownership.",
    done: false,
  },
  {
    title: "Invite members",
    detail: "Import active members, renewal dates, payment status, and assigned trainers.",
    done: false,
  },
];

const trainerSteps = [
  "Complete trainer profile",
  "Review assigned clients",
  "Clear AI-generated plan approvals",
  "Open today’s follow-up queue",
];

const memberSteps = [
  "Select goals",
  "Enter body metrics",
  "Choose diet preferences",
  "Generate first AI plan",
  "Start first workout",
];

export function BusinessOnboardingPage() {
  const org = usePrimaryOrganization();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState("");

  async function runAction(name: string, action: () => Promise<unknown>, success: string) {
    setSaving(name);
    setError("");
    setMessage("");
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: ["organizations"] });
      await queryClient.invalidateQueries({ queryKey: ["business-dashboard"] });
      setMessage(success);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setSaving("");
    }
  }

  function createOrg(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") || "FitGen Performance Club");
    runAction(
      "organization",
      () =>
        api.createOrganization({
          name,
          slug: String(form.get("slug") || name.toLowerCase().replace(/[^a-z0-9]+/g, "-")),
          legal_name: name,
          phone: String(form.get("phone") || ""),
          email: String(form.get("email") || ""),
          address: String(form.get("address") || ""),
          timezone: "Asia/Kolkata",
        }),
      "Organization created.",
    );
  }

  function createPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!org.organization) return;
    const form = new FormData(event.currentTarget);
    runAction(
      "plan",
      () =>
        api.createMembershipPlan(org.organization!.id, {
          name: String(form.get("name") || "Monthly Coaching"),
          duration_days: Number(form.get("duration_days") || 30),
          price_amount: Number(form.get("price_amount") || 3500),
          currency: "INR",
          description: "Created from onboarding",
        }),
      "Membership plan created.",
    );
  }

  function addStaff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!org.organization) return;
    const form = new FormData(event.currentTarget);
    runAction(
      "staff",
      () => api.addStaff(org.organization!.id, { account_id: Number(form.get("account_id")), role: String(form.get("role") || "trainer") }),
      "Staff account linked.",
    );
  }

  function addMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!org.organization) return;
    const form = new FormData(event.currentTarget);
    runAction(
      "member",
      () =>
        api.createOrganizationMember(org.organization!.id, {
          name: String(form.get("name") || "New Member"),
          age: Number(form.get("age") || 30),
          height_cm: Number(form.get("height_cm") || 174),
          weight_kg: Number(form.get("weight_kg") || 76),
          fitness_goal: String(form.get("fitness_goal") || "fat_loss"),
          diet_preference: String(form.get("diet_preference") || "non_veg"),
          budget_amount: Number(form.get("budget_amount") || 250),
          budget_period: "daily",
          location: String(form.get("location") || "Bengaluru, India"),
          gym_type: "premium_gym",
          member_code: String(form.get("member_code") || `FG-${Date.now().toString().slice(-4)}`),
          assigned_trainer_id: form.get("assigned_trainer_id") ? Number(form.get("assigned_trainer_id")) : null,
          account_id: null,
          status: "active",
          joined_on: new Date().toISOString().slice(0, 10),
        }),
      "Member created and first plan generated.",
    );
  }

  const steps = businessSteps.map((step) => ({
    ...step,
    done: step.title === "Create organization" ? Boolean(org.organization) : step.done,
  }));

  return (
    <div className="grid gap-6">
      <header className="rounded-lg border bg-card p-6 shadow-soft">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Setup workspace</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Launch your gym operating system</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          This onboarding keeps owners focused on the operational data needed for retention, revenue, and trainer workflows.
        </p>
      </header>
      <section className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle>Owner setup checklist</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {steps.map((step) => (
              <div className="flex gap-3 rounded-md border p-4" key={step.title}>
                {step.done ? <CheckCircle2 className="mt-0.5 text-emerald-600" size={18} /> : <Circle className="mt-0.5 text-muted-foreground" size={18} />}
                <div>
                  <p className="font-medium">{step.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{step.detail}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Setup actions</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            {message ? <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p> : null}
            {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
            <form className="grid gap-2" onSubmit={createOrg}>
              <Input name="name" placeholder="Gym name" defaultValue="FitGen Performance Club" />
              <Input name="slug" placeholder="gym-slug" defaultValue="fitgen-performance-club" />
              <Input name="email" placeholder="ops@gym.com" />
              <Input name="phone" placeholder="+91..." />
              <Input name="address" placeholder="Address" />
              <Button disabled={saving === "organization"} type="submit">{saving === "organization" ? "Creating..." : "Create organization"}</Button>
            </form>
            <form className="grid gap-2 border-t pt-4" onSubmit={createPlan}>
              <Input name="name" placeholder="Plan name" defaultValue="Monthly Coaching" />
              <Input name="duration_days" type="number" placeholder="30" defaultValue={30} />
              <Input name="price_amount" type="number" placeholder="3500" defaultValue={3500} />
              <Button disabled={!org.organization || saving === "plan"} type="submit">Create membership plan</Button>
            </form>
            <form className="grid gap-2 border-t pt-4" onSubmit={addStaff}>
              <Input name="account_id" type="number" placeholder="Existing trainer account id" />
              <Input name="role" placeholder="trainer" defaultValue="trainer" />
              <Button disabled={!org.organization || saving === "staff"} type="submit">
                <Mail className="mr-2 h-4 w-4" />
                Link trainer/admin
              </Button>
            </form>
            <form className="grid gap-2 border-t pt-4" onSubmit={addMember}>
              <Input name="name" placeholder="Member name" />
              <Input name="member_code" placeholder="Member code" />
              <Input name="assigned_trainer_id" type="number" placeholder="Trainer account id" />
              <div className="grid grid-cols-2 gap-2">
                <Input name="age" type="number" placeholder="Age" defaultValue={30} />
                <Input name="weight_kg" type="number" placeholder="Weight" defaultValue={76} />
                <Input name="height_cm" type="number" placeholder="Height" defaultValue={174} />
                <Input name="budget_amount" type="number" placeholder="Budget" defaultValue={250} />
              </div>
              <Input name="fitness_goal" placeholder="fat_loss" defaultValue="fat_loss" />
              <Input name="diet_preference" placeholder="non_veg" defaultValue="non_veg" />
              <Input name="location" placeholder="Bengaluru, India" defaultValue="Bengaluru, India" />
              <Button disabled={!org.organization || saving === "member"} type="submit">Invite/create member</Button>
            </form>
            <Link className="inline-flex h-10 items-center justify-center rounded-md border bg-card px-4 text-sm font-medium hover:bg-muted" to="/business">
              Go to dashboard
            </Link>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

export function TrainerOnboardingPage() {
  const org = usePrimaryOrganization();
  const clients = useQuery({
    queryKey: ["trainer-clients", org.organization?.id],
    queryFn: () => api.trainerClients(org.organization!.id),
    enabled: Boolean(org.organization?.id),
  });
  const approvals = useQuery({
    queryKey: ["trainer-approvals", org.organization?.id],
    queryFn: () => api.pendingApprovals(org.organization!.id),
    enabled: Boolean(org.organization?.id),
  });
  return (
    <div className="grid gap-6">
      <RoleOnboarding
        eyebrow="Trainer setup"
        title="Start with assigned clients and plan approvals"
        subtitle="Trainers should land with clear work: who needs attention, which AI plans need review, and which clients are slipping."
        icon={Users}
        steps={trainerSteps}
        cta="/business/actions"
        ctaLabel="Open trainer queue"
      />
      <Card>
        <CardHeader><CardTitle>Assigned work preview</CardTitle></CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <div className="rounded-md border p-4"><strong>{clients.data?.length || 0}</strong><p className="text-sm text-muted-foreground">assigned clients</p></div>
          <div className="rounded-md border p-4"><strong>{approvals.data?.length || 0}</strong><p className="text-sm text-muted-foreground">AI plans awaiting review</p></div>
        </CardContent>
      </Card>
    </div>
  );
}

export function MemberOnboardingPage() {
  const auth = useAuth();
  const profileId = useActiveProfileId(auth.profile);
  const queryClient = useQueryClient();
  const dashboard = useQuery({ queryKey: ["member-dashboard", profileId], queryFn: () => api.memberDashboard(profileId!), enabled: Boolean(profileId) });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState("");
  const organizationId = dashboard.data?.user.organization_id;
  const firstExercise = useMemo(() => dashboard.data?.current_workout_plan?.days?.[0]?.exercises?.[0], [dashboard.data]);

  async function run(name: string, action: () => Promise<unknown>, success: string) {
    setSaving(name);
    setMessage("");
    setError("");
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: ["member-dashboard", profileId] });
      setMessage(success);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setSaving("");
    }
  }

  function submitGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!organizationId || !profileId) return;
    const form = new FormData(event.currentTarget);
    run(
      "goal",
      () =>
        api.createGoal(organizationId, profileId, {
          goal_type: String(form.get("goal_type") || "consistency"),
          title: String(form.get("title") || "Train 12 times this month"),
          target_value: Number(form.get("target_value") || 12),
          current_value: 0,
          unit: String(form.get("unit") || "sessions"),
          starts_on: new Date().toISOString().slice(0, 10),
          target_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
        }),
      "Goal saved.",
    );
  }

  function submitMetrics(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!organizationId || !profileId) return;
    const form = new FormData(event.currentTarget);
    run(
      "metrics",
      () =>
        api.createBodyMetrics(organizationId, profileId, {
          measured_on: new Date().toISOString().slice(0, 10),
          weight_kg: Number(form.get("weight_kg") || dashboard.data?.user.weight_kg || 75),
          body_fat_pct: form.get("body_fat_pct") ? Number(form.get("body_fat_pct")) : null,
          waist_cm: form.get("waist_cm") ? Number(form.get("waist_cm")) : null,
          notes: "Recorded from member onboarding",
        }),
      "Body metrics saved.",
    );
  }

  return (
    <div className="grid gap-6">
      <RoleOnboarding
        eyebrow="Member setup"
        title="Build the first coaching loop"
        subtitle="Members should move from goals and body metrics into a first plan and first workout without feeling like they are in an admin system."
        icon={Dumbbell}
        steps={memberSteps}
        cta="/app"
        ctaLabel="Open member app"
      />
      {message ? <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p> : null}
      {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
      <section className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Goals and metrics</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            <form className="grid gap-2" onSubmit={submitGoal}>
              <Input name="title" defaultValue="Train 12 times this month" />
              <Input name="goal_type" defaultValue="consistency" />
              <div className="grid grid-cols-2 gap-2">
                <Input name="target_value" type="number" defaultValue={12} />
                <Input name="unit" defaultValue="sessions" />
              </div>
              <Button disabled={!organizationId || saving === "goal"} type="submit">Save goal</Button>
            </form>
            <form className="grid gap-2 border-t pt-4" onSubmit={submitMetrics}>
              <Input name="weight_kg" type="number" defaultValue={dashboard.data?.user.weight_kg || 75} />
              <Input name="body_fat_pct" type="number" placeholder="Body fat %" />
              <Input name="waist_cm" type="number" placeholder="Waist cm" />
              <Button disabled={!organizationId || saving === "metrics"} type="submit">Save body metrics</Button>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>First plan and workout</CardTitle></CardHeader>
          <CardContent className="grid gap-3">
            <Button disabled={!profileId || saving === "plan"} onClick={() => profileId && run("plan", () => api.generateWeeklyPlan(profileId), "First plan generated.")}>Generate first AI plan</Button>
            <Button
              disabled={!profileId || !firstExercise || saving === "workout"}
              variant="secondary"
              onClick={() =>
                profileId &&
                firstExercise &&
                run(
                  "workout",
                  () =>
                    api.logWorkout(profileId, {
                      planned_exercise_id: firstExercise.id,
                      exercise_name: firstExercise.name,
                      performed_on: new Date().toISOString().slice(0, 10),
                      sets_completed: 3,
                      reps_completed: 10,
                      weight_kg: firstExercise.target_weight_kg || 20,
                      completed: true,
                      perceived_effort: 7,
                    }),
                  "First workout logged.",
                )
              }
            >
              Log first workout
            </Button>
            <p className="text-sm text-muted-foreground">These actions use the existing planning and workout APIs, so onboarding immediately feeds the member dashboard.</p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function RoleOnboarding({
  eyebrow,
  title,
  subtitle,
  icon: Icon,
  steps,
  cta,
  ctaLabel,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  icon: any;
  steps: string[];
  cta: string;
  ctaLabel: string;
}) {
  return (
    <div className="grid gap-6">
      <header className="rounded-lg border bg-card p-6 shadow-soft">
        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg bg-foreground text-background">
          <Icon size={20} />
        </div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{eyebrow}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">{subtitle}</p>
      </header>
      <Card>
        <CardContent className="grid gap-3 pt-5">
          {steps.map((step, index) => (
            <div className="flex items-center gap-3 rounded-md border p-3" key={step}>
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-sm font-semibold">{index + 1}</span>
              <p className="font-medium">{step}</p>
            </div>
          ))}
          <Link className="mt-2 inline-flex h-10 w-fit items-center justify-center rounded-md border border-primary bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90" to={cta}>
            {ctaLabel}
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
