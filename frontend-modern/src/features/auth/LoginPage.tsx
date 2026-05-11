import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthLayout } from "@/layouts/AuthLayout";
import { useAuth } from "@/hooks/useAuth";

export function LoginPage({ audience }: { audience: "business" | "member" }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const isBusiness = audience === "business";

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await auth.login({ email, password });
      navigate(isBusiness ? "/business" : "/app", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in.");
    } finally {
      setLoading(false);
    }
  }

  async function startDemo() {
    if (!isBusiness) return;
    setError("");
    setLoading(true);
    try {
      await auth.startBusinessDemo();
      navigate("/business/onboarding", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load demo workspace.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      audience={audience}
      title={isBusiness ? "Run retention, revenue, and coaching operations in one place." : "Your training plan, progress, and transformation in one calm app."}
      subtitle={
        isBusiness
          ? "A focused workspace for gym owners, admins, and trainers to manage members, renewals, performance, and daily follow-ups."
          : "A mobile-first member experience for workout execution, goals, readiness, and visible progress."
      }
    >
      <form className="grid gap-4" onSubmit={onSubmit}>
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">{isBusiness ? "Business login" : "Member login"}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {isBusiness ? "Use your gym owner, admin, or trainer account." : "Use the member account attached to your profile."}
          </p>
        </div>
        <label className="grid gap-2 text-sm font-medium">
          Email
          <Input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required placeholder="you@example.com" />
        </label>
        <label className="grid gap-2 text-sm font-medium">
          Password
          <Input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required placeholder="Password" />
        </label>
        {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        <Button disabled={loading} type="submit">
          {loading ? "Signing in..." : "Continue"}
        </Button>
        {isBusiness ? (
          <Button disabled={loading} type="button" variant="secondary" onClick={startDemo}>
            Load demo gym workspace
          </Button>
        ) : null}
      </form>
    </AuthLayout>
  );
}
