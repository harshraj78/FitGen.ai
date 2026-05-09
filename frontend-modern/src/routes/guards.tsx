import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

export function RequireAuth({ redirectTo }: { redirectTo: string }) {
  const auth = useAuth();
  const location = useLocation();
  if (auth.isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">Loading session...</div>;
  }
  if (!auth.isAuthenticated) {
    return <Navigate to={redirectTo} replace state={{ from: location }} />;
  }
  return <Outlet />;
}
