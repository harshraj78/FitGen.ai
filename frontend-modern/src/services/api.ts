import type { AccountSignupPayload, AuthResponse, BusinessDashboard, BusinessSignupPayload, Dashboard, GymTransformation, Organization, OrganizationContext } from "./types";

const TOKEN_KEY = "fitgen-auth-token";
const PROFILE_KEY = "fitgen-active-user-id";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "";

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
  const response = await fetch(`${API_BASE_URL}${path}`, {
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

export const api = {
  login(payload: { email: string; password: string }) {
    return request<AuthResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(payload) });
  },
  signup(payload: AccountSignupPayload) {
    return request<AuthResponse>("/api/auth/signup", { method: "POST", body: JSON.stringify(payload) });
  },
  createOrganization(payload: { name: string; slug: string; legal_name?: string; timezone?: string; phone?: string; email?: string; address?: string }) {
    return request<Organization>("/api/organizations", { method: "POST", body: JSON.stringify(payload) });
  },
  async businessSignup(payload: BusinessSignupPayload) {
    const session = await request<AuthResponse>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        password: payload.password,
        profile: {
          name: payload.ownerName,
          age: 30,
          height_cm: 170,
          weight_kg: 70,
          fitness_goal: "maintenance",
          diet_preference: "veg",
          budget_amount: 250,
          budget_period: "daily",
          location: payload.location,
          gym_type: "local_gym",
        },
      }),
    });
    setToken(session.token);
    if (session.profile?.id) {
      setActiveProfileId(session.profile.id);
    }
    const organization = await request<Organization>("/api/organizations", {
      method: "POST",
      body: JSON.stringify({
        name: payload.organizationName,
        slug: slugify(payload.organizationName),
        legal_name: payload.organizationName,
        timezone: "Asia/Kolkata",
        phone: payload.phone || "",
        email: payload.email,
        address: payload.location,
      }),
    });
    return { ...session, organization };
  },
  logout() {
    return request<{ status: string }>("/api/auth/logout", { method: "POST" });
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
  memberDashboard(profileId: number) {
    return request<Dashboard>(`/api/users/${profileId}/dashboard`);
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

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || `gym-${Date.now()}`;
}
