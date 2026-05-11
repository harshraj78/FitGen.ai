import type { AuthResponse, BusinessDashboard, Dashboard, GymTransformation, Organization, OrganizationContext } from "./types";

const TOKEN_KEY = "fitgen-auth-token";
const PROFILE_KEY = "fitgen-active-user-id";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(PROFILE_KEY);
}

export function setActiveProfileId(id: number) {
  localStorage.setItem(PROFILE_KEY, String(id));
}

export function getActiveProfileId() {
  return localStorage.getItem(PROFILE_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const data = await response.json();
      message = data.error?.message || data.detail || message;
    } catch {
      // Keep status text.
    }
    throw new Error(message);
  }
  return response.json();
}

export { request };

export const api = {
  login(payload: { email: string; password: string }) {
    return request<AuthResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(payload) });
  },
  businessDemo() {
    return request<AuthResponse & { organization: any; credentials: Record<string, { email: string; password: string }> }>("/api/demo/business", { method: "POST" });
  },
  me() {
    return request<AuthResponse>("/api/auth/me");
  },
  organizations() {
    return request<Organization[]>("/api/organizations");
  },
  organization(id: number) {
    return request<OrganizationContext>(`/api/organizations/${id}`);
  },
  createOrganization(payload: any) {
    return request<Organization>("/api/organizations", { method: "POST", body: JSON.stringify(payload) });
  },
  createMembershipPlan(organizationId: number, payload: any) {
    return request<any>(`/api/organizations/${organizationId}/membership-plans`, { method: "POST", body: JSON.stringify(payload) });
  },
  addStaff(organizationId: number, payload: { account_id: number; role: string }) {
    return request<any>(`/api/organizations/${organizationId}/staff`, { method: "POST", body: JSON.stringify(payload) });
  },
  createOrganizationMember(organizationId: number, payload: any) {
    return request<any>(`/api/organizations/${organizationId}/members`, { method: "POST", body: JSON.stringify(payload) });
  },
  memberDashboard(profileId: number) {
    return request<Dashboard>(`/api/users/${profileId}/dashboard`);
  },
  createBodyMetrics(organizationId: number, profileId: number, payload: any) {
    return request<any>(`/api/organizations/${organizationId}/business/members/${profileId}/body-metrics`, { method: "POST", body: JSON.stringify(payload) });
  },
  createGoal(organizationId: number, profileId: number, payload: any) {
    return request<any>(`/api/organizations/${organizationId}/members/${profileId}/goals`, { method: "POST", body: JSON.stringify(payload) });
  },
  generateWeeklyPlan(profileId: number) {
    return request<any>(`/api/users/${profileId}/plans/weekly`, { method: "POST" });
  },
  logWorkout(profileId: number, payload: any) {
    return request<any>(`/api/users/${profileId}/workouts/logs`, { method: "POST", body: JSON.stringify(payload) });
  },
  businessDashboard(organizationId: number) {
    return request<BusinessDashboard>(`/api/organizations/${organizationId}/business/dashboard`);
  },
  businessTransformation(organizationId: number) {
    return request<GymTransformation>(`/api/organizations/${organizationId}/business/transformations/gym`);
  },
  trainerClients(organizationId: number) {
    return request<any[]>(`/api/organizations/${organizationId}/trainer/clients`);
  },
  pendingApprovals(organizationId: number) {
    return request<any[]>(`/api/organizations/${organizationId}/trainer/plan-approvals/pending`);
  },
};
