import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

export function usePrimaryOrganization() {
  const organizations = useQuery({ queryKey: ["organizations"], queryFn: api.organizations });
  const organization = organizations.data?.[0];
  const context = useQuery({
    queryKey: ["organization", organization?.id],
    queryFn: () => api.organization(organization!.id),
    enabled: Boolean(organization?.id),
  });

  return {
    organization,
    role: context.data?.role,
    summary: context.data?.summary,
    isLoading: organizations.isLoading || context.isLoading,
    error: organizations.error || context.error,
  };
}
