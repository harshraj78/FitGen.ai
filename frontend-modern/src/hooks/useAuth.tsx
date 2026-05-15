import type React from "react";
import { createContext, useContext, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, clearSession, getActiveProfileId, getToken, setActiveProfileId, setToken } from "@/services/api";
import type { Account, BusinessSignupPayload, Profile } from "@/services/types";

type AuthContextValue = {
  account: Account | null;
  profile: Profile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: { email: string; password: string }) => Promise<Profile | null>;
  businessSignup: (payload: BusinessSignupPayload) => Promise<void>;
  startBusinessDemo: () => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [sessionVersion, setSessionVersion] = useState(0);
  const session = useQuery({
    queryKey: ["auth", "me", sessionVersion],
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
        setSessionVersion((version) => version + 1);
        queryClient.setQueryData(["auth", "me", sessionVersion + 1], response);
        return response.profile ?? null;
      },
      async businessSignup(payload) {
        const response = await api.businessSignup(payload);
        setSessionVersion((version) => version + 1);
        queryClient.setQueryData(["auth", "me", sessionVersion + 1], response);
        queryClient.invalidateQueries({ queryKey: ["organizations"] });
      },
      async startBusinessDemo() {
        const response = await api.businessDemo();
        setToken(response.token);
        setSessionVersion((version) => version + 1);
        queryClient.setQueryData(["auth", "me", sessionVersion + 1], response);
      },
      logout() {
        void api.logout().catch(() => undefined);
        clearSession();
        queryClient.clear();
        setSessionVersion((version) => version + 1);
      },
    }),
    [queryClient, session.data, session.isLoading, sessionVersion],
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
