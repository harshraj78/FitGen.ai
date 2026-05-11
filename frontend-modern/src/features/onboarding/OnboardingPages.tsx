import { CheckCircle2, Circle, Dumbbell, Mail, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

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
            {businessSteps.map((step) => (
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
            <CardTitle>Quick invites</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Input placeholder="trainer@example.com" />
            <Input placeholder="member@example.com" />
            <Button type="button">
              <Mail className="mr-2 h-4 w-4" />
              Prepare invites
            </Button>
            <p className="text-sm text-muted-foreground">Invite sending will connect to notification channels in a later slice.</p>
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
  return (
    <RoleOnboarding
      eyebrow="Trainer setup"
      title="Start with assigned clients and plan approvals"
      subtitle="Trainers should land with clear work: who needs attention, which AI plans need review, and which clients are slipping."
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
