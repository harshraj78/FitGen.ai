import { Activity, BarChart3, CalendarCheck, ClipboardCheck, LogOut, Target, Users } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/business", label: "Overview", icon: BarChart3 },
  { to: "/business/onboarding", label: "Setup", icon: ClipboardCheck },
  { to: "/business/members", label: "Members", icon: Users },
  { to: "/business/retention", label: "Retention", icon: Activity },
  { to: "/business/trainers", label: "Staff", icon: Users },
  { to: "/business/actions", label: "Daily actions", icon: CalendarCheck },
  { to: "/business/transformation", label: "Transformation", icon: Target },
];

export function BusinessLayout() {
  const auth = useAuth();
  const navigate = useNavigate();
  function signOut() {
    auth.logout();
    navigate("/business/login", { replace: true });
  }
  return (
    <div className="min-h-screen bg-[#f7f7f5]">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r bg-card px-4 py-5 lg:block">
        <div className="mb-8 px-2">
          <p className="text-sm font-semibold">FitGen.ai</p>
          <p className="text-xs text-muted-foreground">Owner-led gym operations</p>
        </div>
        <nav className="grid gap-1">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              end={item.to === "/business"}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground",
                  isActive && "bg-muted text-foreground",
                )
              }
            >
              <item.icon size={17} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="absolute inset-x-4 bottom-5 rounded-lg border bg-muted/40 p-3">
          <p className="truncate text-sm font-medium">{auth.account?.email}</p>
          <Button className="mt-3 w-full" variant="secondary" onClick={signOut}>
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>
      <main className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b bg-card/95 px-4 py-3 backdrop-blur lg:hidden">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold">FitGen.ai</p>
              <p className="text-xs text-muted-foreground">Business workspace</p>
            </div>
            <Button className="h-9 px-3 text-sm" variant="secondary" onClick={signOut}>
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </Button>
          </div>
          <nav className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                end={item.to === "/business"}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-10 items-center justify-center gap-2 rounded-md border px-2 text-sm font-medium text-muted-foreground",
                    isActive && "bg-muted text-foreground",
                  )
                }
              >
                <item.icon size={16} />
                <span className="truncate">{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </header>
        <div className="mx-auto max-w-7xl px-5 py-6 md:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
