import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, Dumbbell, Mail, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { usePrimaryOrganization } from "@/hooks/useOrganization";
import { api } from "@/services/api";
import type { MemberPayload, MembershipPlanPayload } from "@/services/types";

const trainerSteps = [
  "Use owner-as-trainer by default",
  "Add staff only if the gym actually has trainers",
  "Review member follow-ups from the daily action queue",
  "Assign clients later when the gym team grows",
];

const memberSteps = [
  "Select goals",
  "Enter body metrics",
  "Choose diet preferences",
  "Generate first AI plan",
  "Start first workout",
];

const inputClass = "h-10 rounded-md border bg-card px-3 text-sm outline-none ring-primary/20 transition focus:ring-4";

export function BusinessOnboardingPage() {
  const org = usePrimaryOrganization();
  const queryClient = useQueryClient();
  const [planMessage, setPlanMessage] = useState("");
  const [memberMessage, setMemberMessage] = useState("");
  const [planForm, setPlanForm] = useState({
    name: "Monthly Membership",
    duration_days: 30,
    price_amount: 2500,
    currency: "INR",
    description: "Standard monthly access plan",
  });
  const [memberForm, setMemberForm] = useState({
    name: "",
    member_code: "",
    phone: "",
    email: "",
    age: 25,
    height_cm: 170,
    weight_kg: 70,
    fitness_goal: "maintenance",
    diet_preference: "veg",
    budget_amount: 250,
    budget_period: "daily",
    location: "India",
    gym_type: "local_gym",
  });

  const planMutation = useMutation({
    mutationFn: (payload: MembershipPlanPayload) => api.createMembershipPlan(org.organization!.id, payload),
    onSuccess: async () => {
      setPlanMessage("Membership plan created. Revenue dashboards can now use this plan.");
      await queryClient.invalidateQueries({ queryKey: ["business-dashboard", org.organization?.id] });
    },
    onError: (error) => setPlanMessage(error instanceof Error ? error.message : "Could not create membership plan."),
  });

  const memberMutation = useMutation({
    mutationFn: (payload: MemberPayload) => api.createMember(org.organization!.id, payload),
    onSuccess: async () => {
      setMemberMessage("Member created with a starter workout and diet plan.");
      setMemberForm((current) => ({ ...current, name: "", member_code: "", phone: "", email: "" }));
      await queryClient.invalidateQueries({ queryKey: ["organization", org.organization?.id] });
      await queryClient.invalidateQueries({ queryKey: ["business-dashboard", org.organization?.id] });
    },
    onError: (error) => setMemberMessage(error instanceof Error ? error.message : "Could not create member."),
  });

  function submitPlan(event: FormEvent) {
    event.preventDefault();
    setPlanMessage("");
    if (!org.organization) {
      setPlanMessage("Create or load a gym workspace first.");
      return;
    }
    planMutation.mutate({
      ...planForm,
      duration_days: Number(planForm.duration_days),
      price_amount: Number(planForm.price_amount),
    });
  }

  function submitMember(event: FormEvent) {
    event.preventDefault();
    setMemberMessage("");
    if (!org.organization) {
      setMemberMessage("Create or load a gym workspace first.");
      return;
    }
    memberMutation.mutate({
      ...memberForm,
      age: Number(memberForm.age),
      height_cm: Number(memberForm.height_cm),
      weight_kg: Number(memberForm.weight_kg),
      budget_amount: Number(memberForm.budget_amount),
      status: "active",
      joined_on: new Date().toISOString().slice(0, 10),
    });
  }

  const businessSteps = [
    {
      title: "Create organization",
      detail: org.organization ? `${org.organization.name} is ready.` : "Set up the gym profile, location, timezone, and operating contact.",
      done: Boolean(org.organization),
    },
    {
      title: "Create membership plans",
      detail: "Add monthly, quarterly, and annual plans so revenue dashboards have structure.",
      done: planMutation.isSuccess,
    },
    {
      title: "Add first members",
      detail: "Create active members with goals, budget context, location, and gym type.",
      done: memberMutation.isSuccess || Number(org.summary?.active_members || 0) > 0,
    },
    {
      title: "Owner-as-trainer or optional staff",
      detail: "Most Indian gyms can run with the owner as trainer. Add staff only when the gym has a separate trainer team.",
      done: false,
    },
  ];

  return (
    <div className="grid gap-6">
      <header className="rounded-lg border bg-card p-6 shadow-soft">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Setup workspace</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Launch your gym operating system</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Create the minimum operational data your gym needs: a workspace, sellable membership plans, and real members.
        </p>
      </header>

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Owner setup checklist</CardTitle>
            <span className="text-sm text-muted-foreground">{org.organization ? org.organization.name : "No workspace"}</span>
          </CardHeader>
          <CardContent className="grid gap-3">
            {businessSteps.map((step) => (
              <div className="flex gap-3 rounded-md border p-4" key={step.title}>
                {step.done ? <CheckCircle2 className="mt-0.5 text-emerald-600" size={18} /> : <Circle className="mt-0.5 text-muted-foreground" size={18} />}
                <div>
                  <p className="font-medium">{step.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{step.detail}</p>
                </div>
              </div>
            ))}
            <div className="rounded-md border bg-muted/40 p-4 text-sm text-muted-foreground">
              Active members: <strong className="text-foreground">{org.summary?.active_members ?? 0}</strong>
              <br />
              Overdue payments: <strong className="text-foreground">{org.summary?.overdue_payments ?? 0}</strong>
            </div>
            <Link className="inline-flex h-10 items-center justify-center rounded-md border bg-card px-4 text-sm font-medium hover:bg-muted" to="/business">
              Go to dashboard
            </Link>
          </CardContent>
        </Card>

        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Create membership plan</CardTitle>
              <span className="text-sm text-muted-foreground">Used for renewals and revenue tracking</span>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={submitPlan}>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="grid gap-2 text-sm font-medium">
                    Plan name
                    <Input value={planForm.name} onChange={(event) => setPlanForm({ ...planForm, name: event.target.value })} required />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Duration days
                    <Input type="number" min={1} max={3700} value={planForm.duration_days} onChange={(event) => setPlanForm({ ...planForm, duration_days: Number(event.target.value) })} required />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Price
                    <Input type="number" min={0} step="0.01" value={planForm.price_amount} onChange={(event) => setPlanForm({ ...planForm, price_amount: Number(event.target.value) })} required />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Currency
                    <Input value={planForm.currency} onChange={(event) => setPlanForm({ ...planForm, currency: event.target.value.toUpperCase() })} required />
                  </label>
                </div>
                <label className="grid gap-2 text-sm font-medium">
                  Description
                  <Input value={planForm.description} onChange={(event) => setPlanForm({ ...planForm, description: event.target.value })} />
                </label>
                {planMessage ? <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">{planMessage}</p> : null}
                <Button disabled={planMutation.isPending || !org.organization} type="submit">
                  {planMutation.isPending ? "Creating plan..." : "Create membership plan"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Add first member</CardTitle>
              <span className="text-sm text-muted-foreground">Creates coaching data for retention workflows</span>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={submitMember}>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="grid gap-2 text-sm font-medium">
                    Member name
                    <Input value={memberForm.name} onChange={(event) => setMemberForm({ ...memberForm, name: event.target.value })} required placeholder="Aarav Sharma" />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Member code
                    <Input value={memberForm.member_code} onChange={(event) => setMemberForm({ ...memberForm, member_code: event.target.value })} placeholder="FG-001" />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    WhatsApp phone
                    <Input value={memberForm.phone} onChange={(event) => setMemberForm({ ...memberForm, phone: event.target.value })} placeholder="+91 98765 43210" />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Email
                    <Input type="email" value={memberForm.email} onChange={(event) => setMemberForm({ ...memberForm, email: event.target.value })} placeholder="member@example.com" />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Age
                    <Input type="number" min={13} max={90} value={memberForm.age} onChange={(event) => setMemberForm({ ...memberForm, age: Number(event.target.value) })} required />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Location
                    <Input value={memberForm.location} onChange={(event) => setMemberForm({ ...memberForm, location: event.target.value })} required />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Height cm
                    <Input type="number" min={101} max={229} value={memberForm.height_cm} onChange={(event) => setMemberForm({ ...memberForm, height_cm: Number(event.target.value) })} required />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Weight kg
                    <Input type="number" min={31} max={249} step="0.1" value={memberForm.weight_kg} onChange={(event) => setMemberForm({ ...memberForm, weight_kg: Number(event.target.value) })} required />
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Goal
                    <select className={inputClass} value={memberForm.fitness_goal} onChange={(event) => setMemberForm({ ...memberForm, fitness_goal: event.target.value })}>
                      <option value="fat_loss">Fat loss</option>
                      <option value="muscle_gain">Muscle gain</option>
                      <option value="maintenance">Maintenance</option>
                    </select>
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Diet
                    <select className={inputClass} value={memberForm.diet_preference} onChange={(event) => setMemberForm({ ...memberForm, diet_preference: event.target.value })}>
                      <option value="veg">Veg</option>
                      <option value="non_veg">Non-veg</option>
                    </select>
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Gym type
                    <select className={inputClass} value={memberForm.gym_type} onChange={(event) => setMemberForm({ ...memberForm, gym_type: event.target.value })}>
                      <option value="home">Home</option>
                      <option value="local_gym">Local gym</option>
                      <option value="premium_gym">Premium gym</option>
                    </select>
                  </label>
                  <label className="grid gap-2 text-sm font-medium">
                    Food budget
                    <Input type="number" min={1} value={memberForm.budget_amount} onChange={(event) => setMemberForm({ ...memberForm, budget_amount: Number(event.target.value) })} required />
                  </label>
                </div>
                {memberMessage ? <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">{memberMessage}</p> : null}
                <Button disabled={memberMutation.isPending || !org.organization} type="submit">
                  {memberMutation.isPending ? "Creating member..." : "Add member"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick invites</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <Input placeholder="trainer@example.com" />
              <Input placeholder="member@example.com" />
              <Button type="button" variant="secondary">
                <Mail className="mr-2 h-4 w-4" />
                Prepare invites
              </Button>
              <p className="text-sm text-muted-foreground">Invite sending will connect to notification channels in a later slice.</p>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}

export function TrainerOnboardingPage() {
  return (
    <RoleOnboarding
      eyebrow="Trainer setup"
      title="Start with assigned clients and plan approvals"
      subtitle="For many Indian gyms, the owner handles coaching too. Use this workspace for owner-led follow-ups first, then add staff when needed."
      icon={Users}
      steps={trainerSteps}
      cta="/business/actions"
      ctaLabel="Open trainer queue"
    />
  );
}

export function MemberOnboardingPage() {
  return (
    <RoleOnboarding
      eyebrow="Member setup"
      title="Build the first coaching loop"
      subtitle="Members should move from goals and body metrics into a first plan and first workout without feeling like they are in an admin system."
      icon={Dumbbell}
      steps={memberSteps}
      cta="/app"
      ctaLabel="Open member app"
    />
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
