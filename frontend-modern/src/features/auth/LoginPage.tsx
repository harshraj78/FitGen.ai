import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthLayout } from "@/layouts/AuthLayout";
import { useAuth } from "@/hooks/useAuth";

export function LoginPage({ audience }: { audience: "business" | "member" }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("India");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const isBusiness = audience === "business";
  const isSignup = isBusiness && mode === "signup";

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isSignup) {
        await auth.businessSignup({
          email,
          password,
          ownerName,
          organizationName,
          phone,
          location,
        });
        navigate("/business/onboarding", { replace: true });
      } else {
        await auth.login({ email, password });
        navigate(isBusiness ? "/business" : "/app", { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : isSignup ? "Could not create workspace." : "Could not sign in.");
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
          <h2 className="text-2xl font-semibold tracking-tight">
            {isBusiness ? (isSignup ? "Create business workspace" : "Business login") : "Member login"}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {isBusiness
              ? isSignup
                ? "Create the owner account and first gym workspace. You can add trainers and members next."
                : "Use your gym owner, admin, or trainer account."
              : "Use the member account attached to your profile."}
          </p>
        </div>
        {isBusiness ? (
          <div className="grid grid-cols-2 gap-2 rounded-md bg-muted p-1">
            <button
              className={`h-9 rounded-md text-sm font-medium ${!isSignup ? "bg-card shadow-sm" : "text-muted-foreground"}`}
              type="button"
              onClick={() => {
                setError("");
                setMode("login");
              }}
            >
              Log in
            </button>
            <button
              className={`h-9 rounded-md text-sm font-medium ${isSignup ? "bg-card shadow-sm" : "text-muted-foreground"}`}
              type="button"
              onClick={() => {
                setError("");
                setMode("signup");
              }}
            >
              Create workspace
            </button>
          </div>
        ) : null}
        {isSignup ? (
          <>
            <label className="grid gap-2 text-sm font-medium">
              Owner name
              <Input value={ownerName} onChange={(event) => setOwnerName(event.target.value)} required placeholder="Your name" />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Gym name
              <Input value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} required placeholder="FitGen Performance Gym" />
            </label>
          </>
        ) : null}
        <label className="grid gap-2 text-sm font-medium">
          Email
          <Input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required placeholder="you@example.com" />
        </label>
        <label className="grid gap-2 text-sm font-medium">
          Password
          <Input value={password} onChange={(event) => setPassword(event.target.value)} type="password" minLength={isSignup ? 8 : undefined} required placeholder={isSignup ? "8+ characters" : "Password"} />
        </label>
        {isSignup ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-2 text-sm font-medium">
              Phone
              <Input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+91..." />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Location
              <Input value={location} onChange={(event) => setLocation(event.target.value)} required placeholder="Noida, India" />
            </label>
          </div>
        ) : null}
        {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        <Button disabled={loading} type="submit">
          {loading ? (isSignup ? "Creating workspace..." : "Signing in...") : isSignup ? "Create workspace" : "Continue"}
        </Button>
        {isBusiness && !isSignup ? (
          <Button disabled={loading} type="button" variant="secondary" onClick={startDemo}>
            Load demo gym workspace
          </Button>
        ) : null}
      </form>
    </AuthLayout>
  );
}
