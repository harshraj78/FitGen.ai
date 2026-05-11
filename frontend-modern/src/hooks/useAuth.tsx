import type React from "react";
import { createContext, useContext, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, clearSession, getActiveProfileId, getToken, setActiveProfileId, setToken } from "@/services/api";
import type { Account, Profile } from "@/services/types";

type AuthContextValue = {
  account: Account | null;
  profile: Profile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: { email: string; password: string }) => Promise<Profile | null>;
  startBusinessDemo: () => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const session = useQuery({
    queryKey: ["auth", "me"],
    queryFn: api.me,
    enabled: Boolean(getToken()),
    retry: false,
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      account: session.data?.account ?? null,
      profile: session.data?.profile ?? null,
      isAuthenticated: Boolean(getToken() && session.data?.account),
      isLoading: session.isLoading,
      async login(payload) {
        const response = await api.login(payload);
        setToken(response.token);
        if (response.profile?.id) {
          setActiveProfileId(response.profile.id);
        }
        queryClient.setQueryData(["auth", "me"], response);
        return response.profile ?? null;
      },
      async startBusinessDemo() {
        const response = await api.businessDemo();
        setToken(response.token);
        queryClient.setQueryData(["auth", "me"], response);
      },
      logout() {
        clearSession();
        queryClient.clear();
      },
    }),
    [queryClient, session.data, session.isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}

export function useActiveProfileId(profile?: Profile | null) {
  const saved = getActiveProfileId();
  return saved ? Number(saved) : profile?.id;
}
