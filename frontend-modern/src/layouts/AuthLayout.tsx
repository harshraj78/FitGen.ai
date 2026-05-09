import type React from "react";
import { Dumbbell, LineChart } from "lucide-react";
import { Link } from "react-router-dom";

export function AuthLayout({
  audience,
  title,
  subtitle,
  children,
}: {
  audience: "business" | "member";
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  const isBusiness = audience === "business";
  return (
    <main className={isBusiness ? "min-h-screen bg-[#f7f7f5]" : "member-surface min-h-screen"}>
      <div className="mx-auto grid min-h-screen max-w-6xl grid-cols-1 gap-8 px-6 py-8 lg:grid-cols-[1fr_440px] lg:items-center">
        <section className="max-w-2xl">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-foreground text-background">
              {isBusiness ? <LineChart size={20} /> : <Dumbbell size={20} />}
            </div>
            <div>
              <p className="text-sm font-semibold">FitGen.ai</p>
              <p className="text-xs text-muted-foreground">{isBusiness ? "Business OS" : "Member app"}</p>
            </div>
          </div>
          <p className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {isBusiness ? "Gym owners, admins, trainers" : "Members and coaching clients"}
          </p>
          <h1 className="max-w-xl text-4xl font-semibold tracking-tight text-foreground md:text-6xl">{title}</h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-muted-foreground">{subtitle}</p>
          <div className="mt-8 flex flex-wrap gap-3 text-sm">
            <Link className="text-primary underline-offset-4 hover:underline" to={isBusiness ? "/app/login" : "/business/login"}>
              {isBusiness ? "Member login" : "Business login"}
            </Link>
          </div>
        </section>
        <section className="rounded-lg border bg-card p-6 shadow-soft">{children}</section>
      </div>
    </main>
  );
}
