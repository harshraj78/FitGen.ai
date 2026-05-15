import { ClipboardCheck, Dumbbell, Home, LogOut, Target, TrendingUp } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/app", label: "Today", icon: Home },
  { to: "/app/onboarding", label: "Setup", icon: ClipboardCheck },
  { to: "/app/workout", label: "Workout", icon: Dumbbell },
  { to: "/app/progress", label: "Progress", icon: TrendingUp },
  { to: "/app/goals", label: "Goals", icon: Target },
];

export function MemberLayout() {
  const auth = useAuth();
  const navigate = useNavigate();
  function signOut() {
    auth.logout();
    navigate("/app/login", { replace: true });
  }
  return (
    <div className="member-surface min-h-screen pb-24">
      <header className="sticky top-0 z-20 border-b bg-white/86 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
          <div>
            <p className="text-sm font-semibold">FitGen.ai</p>
            <p className="text-xs text-muted-foreground">{auth.profile?.name || "Member"}</p>
          </div>
          <Button variant="secondary" onClick={signOut}>
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-5 py-6">
        <Outlet />
      </main>
      <nav className="fixed inset-x-3 bottom-3 z-30 mx-auto grid max-w-lg grid-cols-5 rounded-lg border bg-white/94 p-1 shadow-soft backdrop-blur">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            end={item.to === "/app"}
            to={item.to}
            className={({ isActive }) =>
              cn("grid justify-items-center gap-1 rounded-md px-2 py-2 text-[11px] font-medium text-muted-foreground", isActive && "bg-foreground text-background")
            }
          >
            <item.icon size={17} />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
