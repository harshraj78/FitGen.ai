import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthLayout } from "@/layouts/AuthLayout";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/services/api";

export function MemberInvitePage() {
  const { token = "" } = useParams();
  const auth = useAuth();
  const navigate = useNavigate();
  const [invite, setInvite] = useState<{ member: { name: string; email: string }; organization: { name: string } | null; accepted: boolean } | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    api
      .inviteStatus(token)
      .then((data) => {
        if (!mounted) return;
        setInvite(data);
        setEmail(data.member.email || "");
      })
      .catch((err) => mounted && setError(err instanceof Error ? err.message : "Invite could not be loaded."));
    return () => {
      mounted = false;
    };
  }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("Password confirmation does not match.");
      return;
    }
    setLoading(true);
    try {
      await auth.acceptInvite({ token, email, password, confirm_password: confirmPassword });
      navigate("/app/onboarding", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not activate member account.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      audience="member"
      title="Activate your gym member account."
      subtitle="Set your login once, then use FitGen.ai for workouts, progress, renewals, and follow-ups from your gym."
    >
      <form className="grid gap-4" onSubmit={submit}>
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Accept member invite</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {invite ? `${invite.member.name}${invite.organization ? ` at ${invite.organization.name}` : ""}` : "Loading invite..."}
          </p>
        </div>
        <label className="grid gap-2 text-sm font-medium">
          Email
          <Input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required placeholder="you@example.com" />
        </label>
        <label className="grid gap-2 text-sm font-medium">
          Set password
          <Input value={password} onChange={(event) => setPassword(event.target.value)} type="password" minLength={8} required placeholder="8+ characters" />
        </label>
        <label className="grid gap-2 text-sm font-medium">
          Confirm password
          <Input value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} type="password" minLength={8} required placeholder="Repeat password" />
        </label>
        {invite?.accepted ? <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">This invite has already been accepted.</p> : null}
        {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        <Button disabled={loading || !invite || invite.accepted} type="submit">
          {loading ? "Activating..." : "Activate my account"}
        </Button>
      </form>
    </AuthLayout>
  );
}
