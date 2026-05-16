import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "@/features/auth/LoginPage";
import { MemberInvitePage } from "@/features/auth/MemberInvitePage";
import { BusinessOverview } from "@/features/business/BusinessOverview";
import { DailyActionsPage, MembersPage, RetentionPage, TrainerPerformancePage, TransformationPage } from "@/features/business/BusinessSecondaryPages";
import { GoalsPage, MemberDashboard, ProgressPage, WorkoutPage } from "@/features/member/MemberDashboard";
import { BusinessOnboardingPage, MemberOnboardingPage, TrainerOnboardingPage } from "@/features/onboarding/OnboardingPages";
import { BusinessLayout } from "@/layouts/BusinessLayout";
import { MemberLayout } from "@/layouts/MemberLayout";
import { RequireAuth } from "@/routes/guards";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/business/login" replace />} />
      <Route path="/business/login" element={<LoginPage audience="business" />} />
      <Route path="/app/login" element={<LoginPage audience="member" />} />
      <Route path="/app/invite/:token" element={<MemberInvitePage />} />

      <Route element={<RequireAuth redirectTo="/business/login" />}>
        <Route element={<BusinessLayout />}>
          <Route path="/business" element={<BusinessOverview />} />
          <Route path="/business/onboarding" element={<BusinessOnboardingPage />} />
          <Route path="/business/members" element={<MembersPage />} />
          <Route path="/business/trainer-onboarding" element={<TrainerOnboardingPage />} />
          <Route path="/business/retention" element={<RetentionPage />} />
          <Route path="/business/trainers" element={<TrainerPerformancePage />} />
          <Route path="/business/actions" element={<DailyActionsPage />} />
          <Route path="/business/transformation" element={<TransformationPage />} />
        </Route>
      </Route>

      <Route element={<RequireAuth redirectTo="/app/login" />}>
        <Route element={<MemberLayout />}>
          <Route path="/app" element={<MemberDashboard />} />
          <Route path="/app/onboarding" element={<MemberOnboardingPage />} />
          <Route path="/app/workout" element={<WorkoutPage />} />
          <Route path="/app/progress" element={<ProgressPage />} />
          <Route path="/app/goals" element={<GoalsPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
