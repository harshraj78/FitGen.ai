import { Activity, BarChart3, CalendarCheck, ClipboardCheck, LogOut, Target, Users } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/business", label: "Overview", icon: BarChart3 },
  { to: "/business/onboarding", label: "Setup", icon: ClipboardCheck },
  { to: "/business/retention", label: "Retention", icon: Activity },
  { to: "/business/trainers", label: "Trainers", icon: Users },
  { to: "/business/actions", label: "Daily actions", icon: CalendarCheck },
  { to: "/business/transformation", label: "Transformation", icon: Target },
];

export function BusinessLayout() {
  const auth = useAuth();
  return (
    <div className="min-h-screen bg-[#f7f7f5]">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r bg-card px-4 py-5 lg:block">
        <div className="mb-8 px-2">
          <p className="text-sm font-semibold">FitGen.ai</p>
          <p className="text-xs text-muted-foreground">Gym operating infrastructure</p>
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
          <Button className="mt-3 w-full" variant="secondary" onClick={auth.logout}>
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>
      <main className="lg:pl-72">
        <div className="mx-auto max-w-7xl px-5 py-6 md:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
