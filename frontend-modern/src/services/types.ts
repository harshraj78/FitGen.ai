export type Account = {
  id: number;
  email: string;
};

export type Profile = {
  id: number;
  account_id?: number | null;
  organization_id?: number | null;
  assigned_trainer_id?: number | null;
  name: string;
  phone?: string;
  email?: string;
  fitness_goal: string;
  gym_type: string;
  weight_kg: number;
  height_cm: number;
  member_code?: string;
  status?: string;
  invited_at?: string | null;
  invite_accepted_at?: string | null;
};

export type Organization = {
  id: number;
  name: string;
  slug: string;
  status: string;
};

export type OrganizationContext = {
  organization: Organization;
  role: string;
  summary: {
    active_members: number;
    overdue_payments: number;
  };
};

export type AuthResponse = {
  token: string;
  account: Account;
  profile?: Profile | null;
};

export type AccountSignupPayload = {
  email: string;
  password: string;
  profile: Record<string, unknown>;
};

export type BusinessSignupPayload = {
  email: string;
  password: string;
  ownerName: string;
  organizationName: string;
  phone?: string;
  location: string;
};

export type MembershipPlanPayload = {
  name: string;
  duration_days: number;
  price_amount: number;
  currency: string;
  description?: string;
};

export type MemberPayload = {
  name: string;
  phone?: string;
  email?: string;
  age: number;
  height_cm: number;
  weight_kg: number;
  fitness_goal: string;
  diet_preference: string;
  budget_amount: number;
  budget_period: string;
  location: string;
  gym_type: string;
  member_code?: string;
  status?: string;
  joined_on?: string;
};

export type Dashboard = {
  user: Profile;
  current_workout_plan: any | null;
  current_diet_plan: any | null;
  progress: {
    completion_rate: number;
    total_logs: number;
    current_week_completed: number;
    current_week_planned: number;
    recent_logs: Array<any>;
    chart: Array<any>;
  };
  weekly_summary: any | null;
};

export type BusinessDashboard = {
  organization_id: number;
  revenue: {
    monthly_recurring_revenue: number;
    active_memberships: number;
    expiring_memberships_30d: number;
    unpaid_members: Array<any>;
    overdue_revenue: number;
    renewal_trends: Array<any>;
    retention_trends: Array<any>;
    churn_risk_summary: Record<string, number>;
  };
  renewal_forecast: {
    expiring_memberships: number;
    high_risk_renewals: number;
    forecast_revenue: number;
    revenue_at_risk: number;
    expected_renewals: number;
    renewal_probability: number;
    at_risk_members: Array<any>;
  };
  trainer_performance: Array<any>;
  daily_actions: {
    actions: Array<any>;
    summary: Record<string, number>;
  };
  at_risk_members: Array<any>;
};

export type MemberDetail = {
  member: Profile;
  login_status: "active" | "invited" | "not_invited";
  latest_membership: any | null;
  payments: Array<any>;
  attendance: Array<any>;
  workflows: Array<any>;
  requests: Array<MemberRequest>;
};

export type MemberRequest = {
  id: number;
  organization_id: number;
  member: Profile;
  request_type: string;
  status: string;
  title: string;
  message: string;
  payload: Record<string, unknown>;
  resolution_note: string;
  created_at: string;
};

export type GymTransformation = {
  organization_id: number;
  members_tracked: number;
  members_with_body_improvements: number;
  avg_consistency_improvement: number;
  goal_completion_pct: number;
  milestones_90d: number;
  trainer_success: Array<any>;
};
