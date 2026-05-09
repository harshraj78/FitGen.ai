let state = null;
let currentAccount = null;
let trainerWorkspace = null;
const ACTIVE_USER_KEY = "fitgen-active-user-id";
const AUTH_TOKEN_KEY = "fitgen-auth-token";
let selectedWorkoutDayIndex = null;
let pendingAiWorkoutProposal = null;
let activeSession = null;
let currentDateKey = localDateKey();
let dayRolloverTimer = null;

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

async function api(path, options = {}) {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  });
  if (!response.ok) {
    const message = await errorMessage(response);
    throw new Error(message);
  }
  return response.json();
}

async function errorMessage(response) {
  try {
    const data = await response.json();
    if (Array.isArray(data.detail)) {
      return data.detail.map((item) => item.msg).join(" ");
    }
    if (data.error?.message) {
      return data.error.message;
    }
    return data.detail || response.statusText;
  } catch (error) {
    return response.statusText;
  }
}

async function load() {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const activeUserId = localStorage.getItem(ACTIVE_USER_KEY);
  if (token) {
    try {
      const session = await api("/api/auth/me");
      currentAccount = session.account;
      const profileId = activeUserId || session.profile?.id;
      if (!profileId) {
        showOnboarding("Account found, but no profile exists yet.");
        return;
      }
      localStorage.setItem(ACTIVE_USER_KEY, String(profileId));
      state = await api(`/api/users/${profileId}/dashboard`);
      await loadActiveSession();
      await loadTrainerWorkspace();
      showApp();
      render();
      return;
    } catch (error) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(ACTIVE_USER_KEY);
      showOnboarding("Session expired. Log in again.");
      return;
    }
  }

  if (!activeUserId) {
    showOnboarding();
    return;
  }

  try {
    state = await api(`/api/users/${activeUserId}/dashboard`);
    await loadActiveSession();
    trainerWorkspace = null;
    showApp();
    render();
  } catch (error) {
    localStorage.removeItem(ACTIVE_USER_KEY);
    showOnboarding("Saved profile was not found. Create a new one or load the demo profile.");
  }
}

async function loadActiveSession() {
  if (!state?.user?.id) {
    activeSession = null;
    return;
  }
  const response = await api(`/api/users/${state.user.id}/sessions/active`);
  activeSession = response.session;
  if (activeSession?.day_index) {
    selectedWorkoutDayIndex = activeSession.day_index;
  }
}

async function refreshDashboardAndSession() {
  state = await api(`/api/users/${state.user.id}/dashboard`);
  await loadActiveSession();
  await loadTrainerWorkspace();
  render();
}

async function loadTrainerWorkspace() {
  trainerWorkspace = null;
  if (!currentAccount) return;
  try {
    const organizations = await api("/api/organizations");
    const organization = organizations[0];
    if (!organization) {
      trainerWorkspace = { available: false, reason: "No organization workspace is attached to this account yet." };
      return;
    }
    const [clients, atRisk, approvals, analytics] = await Promise.all([
      api(`/api/organizations/${organization.id}/trainer/clients`),
      api(`/api/organizations/${organization.id}/trainer/clients/at-risk`),
      api(`/api/organizations/${organization.id}/trainer/plan-approvals/pending`),
      api(`/api/organizations/${organization.id}/analytics/trainers/${currentAccount.id}`),
    ]);
    trainerWorkspace = { available: true, organization, clients, atRisk, approvals, analytics };
  } catch (error) {
    trainerWorkspace = { available: false, reason: error.message || "Trainer workspace is not available for this account." };
  }
}

function render() {
  renderProfile();
  renderStats();
  renderCoachCockpit();
  renderCoachStrip();
  renderTrainerWorkspace();
  renderWorkout();
  renderDiet();
  renderReview();
  renderRecentLogs();
  drawVolumeChart();
  $("#exportLink").href = `/api/users/${state.user.id}/report/export`;
  startDayRolloverWatcher();
}

function showOnboarding(message = "") {
  $("#onboarding").classList.add("active");
  $("#onboardingError").textContent = message;
  closeNavDrawer();
}

function showApp() {
  $("#onboarding").classList.remove("active");
}

function renderProfile() {
  const user = state.user;
  $("#profileCard").innerHTML = `
    <strong>${user.name}</strong>
    <span>${label(user.fitness_goal)} | ${label(user.gym_type)}</span>
    <span>${user.weight_kg} kg, ${user.height_cm} cm</span>
    <span>${user.location}</span>
    <span>Budget: Rs ${user.budget_amount}/${user.budget_period}</span>
  `;
  $("#dashboardTitle").textContent = state.current_workout_plan?.title || "No active plan";
}

function renderStats() {
  const progress = state.progress;
  const diet = state.current_diet_plan || {};
  $("#completionRate").textContent = `${Math.round((progress.completion_rate || 0) * 100)}%`;
  $("#totalLogs").textContent = progress.total_logs;
  $("#plannedCompletion").textContent = `${progress.current_week_completed || 0}/${progress.current_week_planned || 0}`;
  $("#calorieTarget").textContent = diet.calories || 0;
  $("#proteinTarget").textContent = `${diet.protein_g || 0}g`;
}

function renderCoachCockpit() {
  const plan = state.current_workout_plan;
  const progress = state.progress || {};
  const todayPlan = plan ? todayPlanContext(plan) : null;
  const completionPercent = Math.round((progress.completion_rate || 0) * 100);
  const insights = adaptiveInsights();
  const primaryInsight = insights[0] || "Log one planned lift and FitGen will start adapting from real performance.";

  $("#coachHeroEyebrow").textContent = todayLabel();
  $("#coachHeroTitle").textContent = todayPlan ? `${todayPlan.day.day}: ${todayPlan.day.focus}` : "No active session";
  $("#coachHeroMeta").textContent = todayPlan
    ? `${formatDateLong(todayPlan.date)} | ${todayPlan.pending} pending, ${todayPlan.completed} done, ${todayPlan.skipped} skipped`
    : "Create or generate a plan to start the adaptive loop.";
  $("#coachHeroInsight").textContent = primaryInsight;
  $("#sessionProgressLabel").textContent = `${completionPercent}%`;
  $("#sessionProgressFill").style.width = `${Math.min(100, Math.max(0, completionPercent))}%`;
  $("#adaptiveInsightList").innerHTML = insights
    .map(
      (insight, index) => `
        <div class="adaptive-insight ${index === 0 ? "primary-insight" : ""}">
          <span>${index + 1}</span>
          <p>${escapeHtml(insight)}</p>
        </div>
      `,
    )
    .join("");
  $("#bestLiftInsight").textContent = bestLiftInsight();
  $("#consistencyInsight").textContent = consistencyInsight();
}

function renderCoachStrip() {
  const plan = state.current_workout_plan;
  const diet = state.current_diet_plan;
  const progress = state.progress || {};
  const todayIndex = plan ? plan.days.findIndex((day) => day.day === currentDayName()) : -1;
  const todayPlanDay = todayIndex >= 0 ? plan.days[todayIndex] : null;
  const nextDay = todayPlanDay || plan?.days?.find((day) => day.exercises.some((exercise) => exercise.status === "pending")) || plan?.days?.[0];
  const nextDayIndex = nextDay ? plan.days.findIndex((day) => day.day === nextDay.day) + 1 : null;
  const nextDate = plan && nextDayIndex ? formatPlanDayDate(plan.week_start, nextDayIndex) : "";
  const pendingCount = nextDay?.exercises?.filter((exercise) => exercise.status === "pending").length || 0;
  $("#coachStrip").innerHTML = `
    <article class="coach-card primary-coach">
      <span>${todayLabel()}</span>
      <strong>${nextDay ? `${escapeHtml(nextDay.day)}: ${escapeHtml(nextDay.focus)}` : "No plan yet"}</strong>
      <p>${nextDay ? `${nextDate}. ${pendingCount} lifts still open for this day.` : "Generate a weekly plan to start tracking."}</p>
    </article>
    <article class="coach-card">
      <span>Plan signal</span>
      <strong>${progress.current_week_completed || 0}/${progress.current_week_planned || 0} completed</strong>
      <p>${progress.current_week_skipped || 0} skipped lifts will influence the next week.</p>
    </article>
    <article class="coach-card">
      <span>Nutrition target</span>
      <strong>${diet?.calories || 0} kcal</strong>
      <p>${diet?.protein_g || 0}g protein with Rs ${Math.round(diet?.estimated_daily_cost || 0)} estimated daily cost.</p>
    </article>
  `;
}

function renderTrainerWorkspace() {
  const root = $("#trainerWorkspaceRoot");
  if (!root) return;
  if (!trainerWorkspace) {
    root.innerHTML = emptyTrainerState("Trainer workspace needs a signed-in organization account.");
    return;
  }
  if (!trainerWorkspace.available) {
    root.innerHTML = emptyTrainerState(trainerWorkspace.reason);
    return;
  }

  const { organization, clients, atRisk, approvals, analytics } = trainerWorkspace;
  const topRisks = atRisk.slice(0, 4);
  root.innerHTML = `
    <div class="trainer-header">
      <div>
        <p class="eyebrow">Trainer workspace</p>
        <h2>${escapeHtml(organization.name)}</h2>
        <p class="muted">Operational queue for assigned clients, AI plan reviews, and adherence risks.</p>
      </div>
      <button id="refreshTrainerWorkspaceBtn" type="button">Refresh workspace</button>
    </div>

    <section class="trainer-kpi-grid">
      ${trainerKpiCard("Assigned clients", analytics.assigned_clients, "Active trainer roster")}
      ${trainerKpiCard("At risk", analytics.at_risk_clients, "Needs trainer follow-up")}
      ${trainerKpiCard("Plan reviews", analytics.pending_plan_reviews, "AI plans waiting")}
      ${trainerKpiCard("Avg adherence", `${Math.round((analytics.average_adherence_rate || 0) * 100)}%`, "Current client execution")}
    </section>

    <section class="trainer-layout">
      <article class="panel trainer-table-panel">
        <header>
          <h3>Assigned clients</h3>
          <span>${clients.length} clients</span>
        </header>
        ${renderAssignedClients(clients)}
      </article>
      <article class="panel">
        <header>
          <h3>At-risk clients</h3>
          <span>Deterministic signals</span>
        </header>
        ${renderAtRiskClients(topRisks)}
      </article>
    </section>

    <section class="trainer-layout lower">
      <article class="panel">
        <header>
          <h3>Pending AI plan approvals</h3>
          <span>${approvals.length} pending</span>
        </header>
        ${renderPlanApprovals(approvals)}
      </article>
      <article class="panel">
        <header>
          <h3>Progress summary</h3>
          <span>Assigned roster</span>
        </header>
        ${renderProgressWidgets(clients)}
      </article>
    </section>
  `;
  $("#refreshTrainerWorkspaceBtn").addEventListener("click", refreshTrainerWorkspace);
  $$("[data-plan-action]").forEach((button) => {
    button.addEventListener("click", () => handlePlanReviewAction(button));
  });
}

function emptyTrainerState(message) {
  return `
    <article class="panel trainer-empty">
      <p class="eyebrow">Trainer workspace</p>
      <h2>Workspace unavailable</h2>
      <p class="muted">${escapeHtml(message || "Sign in with a trainer, admin, or owner account attached to an organization.")}</p>
    </article>
  `;
}

function trainerKpiCard(labelText, value, detail) {
  return `
    <article class="stat trainer-stat">
      <span>${escapeHtml(labelText)}</span>
      <strong>${escapeHtml(String(value ?? 0))}</strong>
      <p>${escapeHtml(detail)}</p>
    </article>
  `;
}

function renderAssignedClients(clients) {
  if (!clients.length) {
    return `<p class="muted">No assigned clients found for this trainer account.</p>`;
  }
  return `
    <div class="client-table">
      <div class="client-row client-head">
        <span>Member</span>
        <span>Active goal</span>
        <span>Adherence</span>
        <span>Latest workout</span>
        <span>Risk</span>
        <span>Membership</span>
      </div>
      ${clients.map((client) => renderClientRow(client)).join("")}
    </div>
  `;
}

function renderClientRow(client) {
  const goal = client.active_goals?.[0];
  const risk = riskLevel(client.risk_signals || []);
  return `
    <div class="client-row">
      <div>
        <strong>${escapeHtml(client.member.name)}</strong>
        <small>${escapeHtml(label(client.member.fitness_goal))}</small>
      </div>
      <span>${goal ? escapeHtml(goal.title) : "No active goal"}</span>
      <span>${percent(client.adherence.adherence_rate)}</span>
      <span>${client.latest_workout.performed_on ? formatDateShort(client.latest_workout.performed_on) : "No workout"}</span>
      <span class="risk-pill ${risk.className}">${risk.label}</span>
      <span>${membershipLabel(client.membership)}</span>
    </div>
  `;
}

function renderAtRiskClients(clients) {
  if (!clients.length) {
    return `<p class="muted">No deterministic risk signals are currently active.</p>`;
  }
  return `
    <div class="risk-list">
      ${clients
        .map(
          (client) => `
          <article class="risk-card">
            <div class="risk-card-head">
              <strong>${escapeHtml(client.member.name)}</strong>
              <span class="risk-pill ${riskLevel(client.risk_signals).className}">${riskLevel(client.risk_signals).label}</span>
            </div>
            <ul>
              ${(client.risk_signals || [])
                .map((signal) => `<li><strong>${escapeHtml(label(signal.code))}</strong><span>${escapeHtml(signal.message)}</span></li>`)
                .join("")}
            </ul>
          </article>
        `,
        )
        .join("")}
    </div>
  `;
}

function renderPlanApprovals(approvals) {
  if (!approvals.length) {
    return `<p class="muted">No AI-generated plans are waiting for trainer review.</p>`;
  }
  return `
    <div class="approval-list">
      ${approvals
        .map(
          (plan) => `
          <article class="approval-card">
            <div>
              <strong>${escapeHtml(plan.member.name)}</strong>
              <p>${escapeHtml(plan.title)}</p>
              <small>${formatDateShort(plan.week_start)} | ${escapeHtml(label(plan.status))}</small>
            </div>
            <p class="muted">${escapeHtml(plan.rationale || "No rationale provided.")}</p>
            <label>Trainer note<textarea data-plan-note="${plan.plan_id}" placeholder="Add approval, modification, or rejection notes"></textarea></label>
            <div class="approval-actions">
              <button class="primary" type="button" data-plan-action="approve" data-plan-id="${plan.plan_id}">Approve</button>
              <button type="button" data-plan-action="modify" data-plan-id="${plan.plan_id}">Mark modified</button>
              <button type="button" data-plan-action="reject" data-plan-id="${plan.plan_id}">Reject</button>
            </div>
          </article>
        `,
        )
        .join("")}
    </div>
  `;
}

function renderProgressWidgets(clients) {
  const adherence = average(clients.map((client) => client.adherence.adherence_rate));
  const attendance = average(clients.map((client) => client.membership.days_remaining === null ? 0 : 1));
  const completion = average(clients.map((client) => client.latest_workout.completion_rate || 0));
  const goals = clients.flatMap((client) => client.active_goals || []);
  const overdueGoals = goals.filter((goal) => goal.target_date && new Date(goal.target_date) < new Date()).length;
  return `
    <div class="progress-widget-grid">
      ${progressWidget("Consistency", percent(adherence), "Average adherence across assigned clients")}
      ${progressWidget("Goal progress", `${Math.max(0, goals.length - overdueGoals)}/${goals.length}`, "Active goals not overdue")}
      ${progressWidget("Attendance trend", percent(attendance), "Clients with active membership context")}
      ${progressWidget("Workout completion", percent(completion), "Latest workout completion average")}
    </div>
  `;
}

function progressWidget(title, value, detail) {
  return `
    <div class="progress-widget">
      <span>${escapeHtml(title)}</span>
      <strong>${escapeHtml(value)}</strong>
      <p>${escapeHtml(detail)}</p>
    </div>
  `;
}

async function refreshTrainerWorkspace() {
  await loadTrainerWorkspace();
  renderTrainerWorkspace();
}

async function handlePlanReviewAction(button) {
  const planId = button.dataset.planId;
  const action = button.dataset.planAction;
  const note = $(`[data-plan-note="${planId}"]`)?.value || "";
  const organizationId = trainerWorkspace?.organization?.id;
  if (!organizationId || !planId) return;
  const status = action === "approve" ? "trainer_approved" : "trainer_modified";
  const defaultNote =
    action === "approve"
      ? "Approved by trainer."
      : action === "reject"
        ? "Rejected by trainer. Generate or modify before assigning."
        : "Modified by trainer before assignment.";
  setButtonLoading(button, true, "Saving...");
  try {
    await api(`/api/organizations/${organizationId}/workout-plans/${planId}/review`, {
      method: "POST",
      body: JSON.stringify({
        status,
        trainer_notes: note.trim() || defaultNote,
      }),
    });
    await refreshTrainerWorkspace();
  } catch (error) {
    button.textContent = error.message || "Failed";
  } finally {
    setButtonLoading(button, false);
  }
}

function todayPlanContext(plan) {
  const todayIndex = plan.days.findIndex((day) => day.day === currentDayName());
  const selectedIndex = todayIndex >= 0 ? todayIndex + 1 : pickWorkoutDay(plan.days);
  const day = plan.days[selectedIndex - 1];
  const summary = summarizeDay(day);
  return {
    day,
    dayIndex: selectedIndex,
    date: isoDateForPlanDay(plan.week_start, selectedIndex),
    completed: summary.completed,
    skipped: summary.skipped,
    pending: summary.pending,
  };
}

function adaptiveInsights() {
  const progress = state.progress || {};
  const logs = progress.recent_logs || [];
  const insights = [];
  const completion = progress.completion_rate || 0;
  const skipped = progress.current_week_skipped || 0;
  const planned = progress.current_week_planned || 0;
  const completed = progress.current_week_completed || 0;
  const highEffortLogs = logs.filter((log) => log.effort >= 9);
  const missedLogs = logs.filter((log) => log.completed === false);

  if (planned > 0) {
    if (completion >= 0.85) {
      insights.push(`Execution is strong at ${Math.round(completion * 100)}%. Next re-plan can apply progressive overload if effort stays controlled.`);
    } else if (completion < 0.55) {
      insights.push(`Only ${completed}/${planned} planned lifts are complete. Next week should reduce volume before adding intensity.`);
    } else {
      insights.push(`${completed}/${planned} planned lifts are complete. Finish today's queue before changing the plan.`);
    }
  }
  if (skipped > 0 || missedLogs.length > 0) {
    insights.push(`${Math.max(skipped, missedLogs.length)} skipped lift signal detected. FitGen should keep substitutions easier next cycle.`);
  }
  if (highEffortLogs.length > 0) {
    insights.push(`${highEffortLogs[0].exercise} recently hit ${highEffortLogs[0].effort}/10 effort. Hold load steady until reps are cleaner.`);
  }
  if (logs.length >= 3) {
    insights.push(`${logs.length} recent logs are feeding your plan memory: load, reps, effort, and completion now matter.`);
  }
  if (!insights.length) {
    insights.push("No workout history yet. Complete or skip planned lifts so the coach can learn honestly.");
    insights.push("Your first useful signal is not max weight. It is whether the planned session was completed cleanly.");
  }
  return insights.slice(0, 4);
}

function bestLiftInsight() {
  const best = state.progress?.best_weights || {};
  const entries = Object.entries(best).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return "Waiting for logs";
  const [exercise, weight] = entries[0];
  return `${exercise}: ${weight} kg`;
}

function consistencyInsight() {
  const progress = state.progress || {};
  const planned = progress.current_week_planned || 0;
  if (!planned) return "No weekly plan yet";
  const done = progress.current_week_completed || 0;
  const skipped = progress.current_week_skipped || 0;
  if (done === planned) return "Week fully resolved";
  if (skipped > done) return "Skipped volume is leading";
  return `${planned - done - skipped} lifts still need a decision`;
}

function renderWorkout() {
  const plan = state.current_workout_plan;
  renderAiWorkoutProposal();
  const isReviewingAiPlan = Boolean(pendingAiWorkoutProposal);
  $("#sessionWorkspace").classList.toggle("hidden", isReviewingAiPlan);
  $("#logPanel").classList.toggle("hidden", isReviewingAiPlan);
  $("#workoutModePill").textContent = isReviewingAiPlan ? "Review AI plan" : activeSession ? "Session active" : "Session ready";
  $("#workoutModePill").classList.toggle("reviewing", isReviewingAiPlan);
  if (!plan) {
    $("#daySelector").innerHTML = "<p>No workout plan yet.</p>";
    $("#sessionSummary").innerHTML = "";
    $("#selectedDayPlan").innerHTML = "";
    $("#finishSessionMessage").textContent = "";
    return;
  }
  if (!$("#equipmentInput").value.trim()) {
    const equipment = [...new Set(plan.days.flatMap((day) => day.exercises.map((exercise) => exercise.equipment)))];
    $("#equipmentInput").value = equipment.filter(Boolean).join(", ");
  }
  if (!selectedWorkoutDayIndex || !plan.days.some((day, index) => index + 1 === selectedWorkoutDayIndex)) {
    selectedWorkoutDayIndex = pickWorkoutDay(plan.days);
  }
  if (activeSession) {
    renderActiveSession();
    return;
  }
  const selectedDay = plan.days[selectedWorkoutDayIndex - 1];
  const selectedDate = isoDateForPlanDay(plan.week_start, selectedWorkoutDayIndex);
  const dayStatuses = summarizeDay(selectedDay);
  $("#workoutTitle").textContent = plan.title;
  $("#sessionMeta").textContent = `${selectedDay.day}, ${formatDateLong(selectedDate)} | ${selectedDay.exercises.length} planned exercises`;
  $("#sessionSummary").innerHTML = `
    <span class="session-summary-chip done">${dayStatuses.completed} done</span>
    <span class="session-summary-chip skipped">${dayStatuses.skipped} skipped</span>
    <span class="session-summary-chip">${dayStatuses.pending} pending</span>
  `;
  $("#daySelector").innerHTML = plan.days
    .map(
      (day, index) => `
      <button type="button" class="day-pill ${selectedWorkoutDayIndex === index + 1 ? "active" : ""}" data-day-index="${index + 1}">
        <strong>${day.day}</strong>
        <span>${formatPlanDayDate(plan.week_start, index + 1)}</span>
      </button>
    `,
    )
    .join("");
  $("#selectedDayPlan").innerHTML = `
    <div class="session-day-head">
      <div>
        <h3>${selectedDay.day}</h3>
        <p class="muted">${selectedDay.focus} | ${formatDateLong(selectedDate)}</p>
      </div>
      <span class="session-badge">${selectedDay.exercises.length} lifts queued</span>
    </div>
    <div class="readiness-card">
      <div class="form-grid compact-grid">
        <label>Energy<input id="readinessEnergy" type="number" min="1" max="10" value="7" /></label>
        <label>Sleep<input id="readinessSleep" type="number" min="1" max="10" value="7" /></label>
        <label>Soreness<input id="readinessSoreness" type="number" min="1" max="10" value="4" /></label>
        <label>Pain<input id="readinessPain" type="number" min="0" max="10" value="0" /></label>
      </div>
      <button id="startSessionBtn" class="primary" type="button">Start this session</button>
    </div>
    ${selectedDay.exercises
      .map(
        (exercise) => `
        <article class="session-exercise">
          <div class="session-exercise-top">
            <div>
              <strong>${exercise.name}</strong>
              <p class="session-exercise-meta">${exercise.sets} sets x ${exercise.target_reps} reps | ${exercise.target_weight_kg || "bodyweight"} kg</p>
            </div>
            <div>
              <span class="budget">${exercise.equipment}</span>
              <span class="session-status ${exercise.status}">${labelExerciseStatus(exercise.status)}</span>
            </div>
          </div>
          <p class="session-exercise-meta">${exercise.notes}</p>
          <div class="session-exercise-actions">
            <button type="button" data-exercise-id="${exercise.id}" data-exercise-name="${exercise.name}" data-target-weight="${exercise.target_weight_kg || 0}">Log this lift</button>
            <button type="button" data-skip-exercise-id="${exercise.id}" data-skip-exercise-name="${exercise.name}">Mark skipped</button>
            <button type="button" data-ask-exercise-name="${exercise.name}">Ask AI</button>
          </div>
        </article>
      `,
      )
      .join("")}
  `;
  $$(".day-pill").forEach((button) => {
    button.addEventListener("click", () => {
      selectedWorkoutDayIndex = Number(button.dataset.dayIndex);
      renderWorkout();
    });
  });
  $("#startSessionBtn").addEventListener("click", startSelectedSession);
  $$(".session-exercise-actions button").forEach((button) => {
    if (button.dataset.exerciseId) {
      button.addEventListener("click", () => {
        loadExerciseIntoLog(button.dataset.exerciseId, button.dataset.exerciseName, button.dataset.targetWeight);
      });
    }
    if (button.dataset.skipExerciseId) {
      button.addEventListener("click", async () => {
        await markExerciseSkipped(button.dataset.skipExerciseId, button.dataset.skipExerciseName);
      });
    }
    if (button.dataset.askExerciseName) {
      button.addEventListener("click", () => {
        $("#exerciseQuestionName").value = button.dataset.askExerciseName;
        $("#exerciseQuestionInput").focus();
        document.querySelector("#exerciseQuestionForm").scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
  });
  const finishButton = $("#finishSessionBtn");
  const allResolved = dayStatuses.pending === 0 && selectedDay.exercises.length > 0;
  finishButton.disabled = !allResolved;
  $("#finishSessionMessage").textContent = allResolved
    ? sessionMessage(dayStatuses)
    : "Finish session unlocks when each planned lift is logged or skipped.";

  const firstExercise = plan.days[0]?.exercises[0]?.name;
  if (firstExercise && !$("input[name='exercise_name']").value) {
    $("input[name='exercise_name']").value = firstExercise;
  }
  $("input[name='performed_on']").value = selectedDate;
}

function renderActiveSession() {
  const plan = state.current_workout_plan;
  const selectedDay = plan.days[(activeSession.day_index || selectedWorkoutDayIndex) - 1] || plan.days[0];
  const completed = activeSession.exercises.filter((exercise) => exercise.status === "completed").length;
  const skipped = activeSession.exercises.filter((exercise) => exercise.status === "skipped").length;
  const pending = activeSession.exercises.length - completed - skipped;
  $("#workoutTitle").textContent = plan.title;
  $("#sessionMeta").textContent = `${selectedDay.day}, ${formatDateLong(activeSession.planned_for)} | active session`;
  $("#sessionSummary").innerHTML = `
    <span class="session-summary-chip done">${completed} done</span>
    <span class="session-summary-chip skipped">${skipped} skipped</span>
    <span class="session-summary-chip">${pending} pending</span>
  `;
  $("#daySelector").innerHTML = plan.days
    .map(
      (day, index) => `
      <button type="button" class="day-pill ${activeSession.day_index === index + 1 ? "active" : ""}" disabled>
        <strong>${day.day}</strong>
        <span>${formatPlanDayDate(plan.week_start, index + 1)}</span>
      </button>
    `,
    )
    .join("");
  $("#selectedDayPlan").innerHTML = `
    <div class="session-day-head">
      <div>
        <h3>${selectedDay.day}</h3>
        <p class="muted">Started ${formatDateLong(activeSession.planned_for)} | ${Math.round((activeSession.completion_rate || 0) * 100)}% complete</p>
      </div>
      <span class="session-badge">Backend session #${activeSession.id}</span>
    </div>
    ${(activeSession.safety || []).map((note) => `<p class="error">${escapeHtml(note)}</p>`).join("")}
    ${activeSession.exercises
      .map(
        (exercise) => `
        <article class="session-exercise">
          <div class="session-exercise-top">
            <div>
              <strong>${escapeHtml(exercise.exercise_name)}</strong>
              <p class="session-exercise-meta">${exercise.target_sets} sets x ${exercise.target_reps} reps | ${exercise.target_weight_kg || "bodyweight"} kg</p>
            </div>
            <div>
              <span class="session-status ${exercise.status}">${labelExerciseStatus(exercise.status)}</span>
            </div>
          </div>
          <div class="performed-set-list">
            ${
              exercise.sets.length
                ? exercise.sets
                    .map(
                      (set) =>
                        `<span class="session-summary-chip">Set ${set.set_number}: ${set.reps} reps, ${set.weight_kg} kg, RPE ${set.perceived_effort}${set.pain_flag ? " pain" : ""}</span>`,
                    )
                    .join("")
                : `<p class="session-exercise-meta">${escapeHtml(exercise.notes || "No sets logged yet.")}</p>`
            }
          </div>
          <div class="session-exercise-actions">
            <button type="button" data-session-exercise-id="${exercise.id}" data-exercise-name="${escapeHtml(exercise.exercise_name)}" data-target-weight="${exercise.target_weight_kg || 0}" ${exercise.status === "skipped" ? "disabled" : ""}>Log set</button>
            <button type="button" data-skip-exercise-id="${exercise.id}" data-skip-exercise-name="${escapeHtml(exercise.exercise_name)}" ${exercise.sets.length || exercise.status === "skipped" ? "disabled" : ""}>Skip</button>
            <button type="button" data-ask-exercise-name="${escapeHtml(exercise.exercise_name)}">Ask AI</button>
          </div>
        </article>
      `,
      )
      .join("")}
  `;
  $$(".session-exercise-actions button").forEach((button) => {
    if (button.dataset.sessionExerciseId) {
      button.addEventListener("click", () => {
        loadSessionExerciseIntoLog(button.dataset.sessionExerciseId, button.dataset.exerciseName, button.dataset.targetWeight);
      });
    }
    if (button.dataset.skipExerciseId) {
      button.addEventListener("click", async () => {
        await markExerciseSkipped(button.dataset.skipExerciseId, button.dataset.skipExerciseName);
      });
    }
    if (button.dataset.askExerciseName) {
      button.addEventListener("click", () => {
        $("#exerciseQuestionName").value = button.dataset.askExerciseName;
        $("#exerciseQuestionInput").focus();
      });
    }
  });
  $("#finishSessionBtn").disabled = pending > 0;
  $("#finishSessionMessage").textContent = pending > 0 ? "Finish unlocks after every exercise is completed or skipped." : "Session is ready to finish.";
  $("input[name='performed_on']").value = activeSession.planned_for || localDateKey();
}

async function startSelectedSession() {
  const response = await api(`/api/users/${state.user.id}/sessions/start`, {
    method: "POST",
    body: JSON.stringify({
      workout_plan_id: state.current_workout_plan.id,
      day_index: selectedWorkoutDayIndex,
      planned_for: isoDateForPlanDay(state.current_workout_plan.week_start, selectedWorkoutDayIndex),
      readiness: {
        energy: Number($("#readinessEnergy").value || 7),
        sleep_quality: Number($("#readinessSleep").value || 7),
        soreness: Number($("#readinessSoreness").value || 4),
        pain: Number($("#readinessPain").value || 0),
      },
    }),
  });
  activeSession = response.session;
  renderWorkout();
}

function renderDiet() {
  const diet = state.current_diet_plan;
  const result = $("#dietAiResult");
  const status = $("#dietAiStatus");
  if (!result.innerHTML) {
    result.classList.add("hidden");
  }
  if (!status.textContent) {
    status.textContent = "Use your real pantry, not a perfect one.";
  }
  if (!diet) {
    $("#dietPlan").innerHTML = "<p>No diet plan yet.</p>";
    return;
  }
  $("#dietPlan").innerHTML = diet.meals
    .map(
      (meal) => `
      <article class="meal">
        <div class="meal-top">
          <h3>${meal.name}</h3>
          <span>${meal.protein_g}g protein</span>
        </div>
        <ul>${meal.items.map((item) => `<li>${item}</li>`).join("")}</ul>
        <p>${meal.calories} kcal</p>
        <span class="budget">Rs ${meal.cost_rs}</span>
      </article>
    `,
    )
    .join("");
}

function renderReview() {
  const review = state.weekly_summary;
  $("#reviewWeek").textContent = review ? `Week of ${review.week_start}` : "Not generated";
  $("#weeklySummary").textContent = review?.summary || "Run the weekly review after logging workouts.";
  $("#weeklyAdjustment").textContent = review?.adjustments || "The next plan will use completion, load, effort, and feedback.";
}

function renderRecentLogs() {
  const logs = state.progress.recent_logs || [];
  $("#recentLogs").innerHTML =
    logs
      .map(
        (log) => `
      <div class="recent-log">
        <span>${log.exercise}<br>${log.sets} sets, ${log.reps} reps, ${log.weight_kg} kg</span>
        <span>${log.effort}/10</span>
      </div>
    `,
      )
      .join("") || "<p class='muted'>No logs yet.</p>";
}

function drawVolumeChart() {
  const canvas = $("#volumeChart");
  const ctx = canvas.getContext("2d");
  const points = state.progress.chart || [];
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const pad = 34;
  const max = Math.max(...points.map((point) => point.volume), 100);
  ctx.strokeStyle = "#d9ded6";
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i += 1) {
    const y = pad + ((canvas.height - pad * 2) / 3) * i;
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(canvas.width - pad, y);
    ctx.stroke();
  }

  if (!points.length) {
    ctx.fillStyle = "#66736c";
    ctx.fillText("Log workouts to build the chart.", pad, canvas.height / 2);
    return;
  }

  const step = (canvas.width - pad * 2) / Math.max(points.length - 1, 1);
  ctx.strokeStyle = "#116b5d";
  ctx.lineWidth = 3;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = pad + step * index;
    const y = canvas.height - pad - (point.volume / max) * (canvas.height - pad * 2);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  points.forEach((point, index) => {
    const x = pad + step * index;
    const y = canvas.height - pad - (point.volume / max) * (canvas.height - pad * 2);
    ctx.fillStyle = point.effort >= 9 ? "#c4512e" : "#e2b044";
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();
  });
}

function label(value) {
  return String(value).replaceAll("_", " ");
}

function percent(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`;
}

function average(values) {
  const valid = values.filter((value) => Number.isFinite(Number(value)));
  if (!valid.length) return 0;
  return valid.reduce((total, value) => total + Number(value), 0) / valid.length;
}

function membershipLabel(membership) {
  if (!membership?.status) return "No membership";
  const suffix = membership.days_remaining === null || membership.days_remaining === undefined ? "" : ` (${membership.days_remaining}d)`;
  return `${label(membership.status)}${suffix}`;
}

function riskLevel(signals = []) {
  if (!signals.length) return { label: "Clear", className: "low" };
  if (signals.some((signal) => signal.severity === "high")) return { label: "High", className: "high" };
  if (signals.length >= 2) return { label: "Medium", className: "medium" };
  return { label: "Watch", className: "medium" };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setButtonLoading(button, isLoading, loadingText) {
  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.textContent = loadingText;
    button.disabled = true;
    return;
  }
  button.textContent = button.dataset.originalText || button.textContent;
  button.disabled = false;
}

function labelExerciseStatus(status) {
  return { completed: "Done", skipped: "Skipped", pending: "Pending" }[status] || "Pending";
}

function pickWorkoutDay(days) {
  const today = currentDayName();
  const matchIndex = days.findIndex((day) => day.day === today);
  return matchIndex >= 0 ? matchIndex + 1 : 1;
}

function loadExerciseIntoLog(exerciseId, exerciseName, targetWeight) {
  $("input[name='planned_exercise_id']").value = exerciseId;
  $("input[name='session_exercise_id']").value = "";
  $("input[name='exercise_name']").value = exerciseName;
  $("input[name='weight_kg']").value = Number(targetWeight || 0);
  $("#selectedExercise").textContent = `Logging planned exercise: ${exerciseName}`;
  document.querySelector("#logForm").scrollIntoView({ behavior: "smooth", block: "center" });
}

function loadSessionExerciseIntoLog(sessionExerciseId, exerciseName, targetWeight) {
  $("input[name='planned_exercise_id']").value = "";
  $("input[name='session_exercise_id']").value = sessionExerciseId;
  $("input[name='exercise_name']").value = exerciseName;
  $("input[name='sets_completed']").value = 1;
  $("input[name='weight_kg']").value = Number(targetWeight || 0);
  $("#selectedExercise").textContent = `Logging one set for active session: ${exerciseName}`;
  document.querySelector("#logForm").scrollIntoView({ behavior: "smooth", block: "center" });
}

function summarizeDay(day) {
  return day.exercises.reduce(
    (summary, exercise) => {
      summary[exercise.status] += 1;
      return summary;
    },
    { completed: 0, skipped: 0, pending: 0 },
  );
}

function sessionMessage(summary) {
  if (summary.skipped > 0) {
    return `${summary.completed} completed, ${summary.skipped} skipped. That will shape the next plan.`;
  }
  return `Session complete. ${summary.completed} planned lifts finished cleanly.`;
}

function renderAiWorkoutProposal() {
  const panel = $("#aiPlanProposal");
  const status = $("#aiPlanStatus");
  if (!pendingAiWorkoutProposal) {
    panel.innerHTML = "";
    panel.classList.add("hidden");
    if (!status.textContent) {
      status.textContent = "Enter the equipment you genuinely have access to.";
    }
    return;
  }
  status.textContent = pendingAiWorkoutProposal.question || "Review the draft, then decide.";
  const grouped = groupProposalDays(pendingAiWorkoutProposal.proposal.days);
  const exerciseCount = pendingAiWorkoutProposal.proposal.days.length;
  const sourceLabel = pendingAiWorkoutProposal.enabled ? "Generated with Groq" : "Deterministic fallback";
  panel.classList.remove("hidden");
  panel.innerHTML = `
    <div class="proposal-review-banner">
      <strong>${sourceLabel}</strong>
      <span>${grouped.length} days | ${exerciseCount} exercises | Accepting replaces the active weekly plan.</span>
    </div>
    <div class="proposal-head">
      <div>
        <strong>${escapeHtml(pendingAiWorkoutProposal.proposal.title)}</strong>
        <p class="muted">${escapeHtml(pendingAiWorkoutProposal.proposal.rationale)}</p>
      </div>
      <span class="budget">${escapeHtml((pendingAiWorkoutProposal.proposal.equipment_summary || []).join(", "))}</span>
    </div>
    <div class="proposal-days">
      ${grouped
        .map(
          (day) => `
          <section class="proposal-day">
            <h4>${escapeHtml(day.day)}</h4>
            <span class="muted">${escapeHtml(day.focus)}</span>
            <ul>
              ${day.exercises
                .map(
                  (exercise) =>
                    `<li><strong>${escapeHtml(exercise.name)}</strong> <span>${exercise.sets} x ${escapeHtml(exercise.target_reps)} | ${escapeHtml(exercise.equipment)}</span></li>`,
                )
                .join("")}
            </ul>
          </section>
        `,
        )
        .join("")}
    </div>
    <div class="ai-actions">
      <button id="acceptAiPlanBtn" class="primary" type="button">Yes, use this plan</button>
      <button id="dismissAiPlanBtn" type="button">Keep current plan</button>
    </div>
  `;
  $("#acceptAiPlanBtn").addEventListener("click", acceptAiPlan);
  $("#dismissAiPlanBtn").addEventListener("click", () => {
    pendingAiWorkoutProposal = null;
    status.textContent = "Keeping your current plan.";
    renderAiWorkoutProposal();
  });
}

function groupProposalDays(days) {
  const grouped = [];
  days.forEach((exercise) => {
    let day = grouped.find((item) => item.day === exercise.day);
    if (!day) {
      day = { day: exercise.day, focus: exercise.focus, exercises: [] };
      grouped.push(day);
    }
    day.exercises.push(exercise);
  });
  return grouped;
}

function appendCommaValue(input, value) {
  const current = input.value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (!current.some((item) => item.toLowerCase() === value.toLowerCase())) {
    current.push(value);
  }
  input.value = current.join(", ");
  input.focus();
}

function localDateKey(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function currentDayName() {
  return DAY_NAMES[new Date().getDay()];
}

function todayLabel() {
  return `Today, ${currentDayName()}`;
}

function parseLocalDate(dateKey) {
  const [year, month, day] = dateKey.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function isoDateForPlanDay(weekStart, dayIndex) {
  return localDateKey(addDays(parseLocalDate(weekStart), dayIndex - 1));
}

function formatPlanDayDate(weekStart, dayIndex) {
  return formatDateShort(isoDateForPlanDay(weekStart, dayIndex));
}

function formatDateShort(dateKey) {
  return parseLocalDate(dateKey).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatDateLong(dateKey) {
  return parseLocalDate(dateKey).toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
}

function startDayRolloverWatcher() {
  if (dayRolloverTimer) return;
  dayRolloverTimer = window.setInterval(() => {
    const nextDateKey = localDateKey();
    if (nextDateKey === currentDateKey) return;
    currentDateKey = nextDateKey;
    selectedWorkoutDayIndex = null;
    if (state) {
      render();
    }
  }, 60000);
}

async function markExerciseSkipped(exerciseId, exerciseName) {
  if (activeSession) {
    const response = await api(`/api/sessions/${activeSession.id}/exercises/${exerciseId}/skip`, {
      method: "POST",
      body: JSON.stringify({ reason: "user_skipped", notes: "" }),
    });
    activeSession = response.session;
    await refreshDashboardAndSession();
    return;
  }
  const performedOn = state.current_workout_plan
    ? isoDateForPlanDay(state.current_workout_plan.week_start, selectedWorkoutDayIndex || pickWorkoutDay(state.current_workout_plan.days))
    : localDateKey();
  await api(`/api/users/${state.user.id}/workouts/logs`, {
    method: "POST",
    body: JSON.stringify({
      planned_exercise_id: Number(exerciseId),
      exercise_name: exerciseName,
      performed_on: performedOn,
      sets_completed: 0,
      reps_completed: 0,
      weight_kg: 0,
      completed: false,
      perceived_effort: 3,
    }),
  });
  await refreshDashboardAndSession();
}

function setAuthMode(mode) {
  $$(".auth-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.authMode === mode);
  });
  $$("[data-auth-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.authPanel === mode);
  });
  if (mode === "signup") {
    setSignupStep("account");
  }
}

function setSignupStep(step) {
  $$("[data-signup-step]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.signupStep === step);
  });
}

function validateSignupAccountStep() {
  const emailInput = $("input[name='email']");
  const passwordInput = $("input[name='password']");
  if (!emailInput.value.trim()) {
    throw new Error("Enter your email.");
  }
  if (!emailInput.checkValidity()) {
    throw new Error("Enter a valid email address.");
  }
  if (!passwordInput.value || passwordInput.value.length < 8) {
    throw new Error("Password must be at least 8 characters.");
  }
}

function syncSignupPreview() {
  const email = $("input[name='email']").value.trim();
  $("input[name='email_confirm']").value = email;
  $("input[name='password_confirm']").value = $("input[name='password']").value;
  $("#accountPreview").textContent = `Account: ${email}`;
}

function profilePayload(form) {
  const payload = Object.fromEntries(new FormData(form).entries());
  return {
    email: payload.email,
    password: payload.password,
    profile: {
      name: payload.name,
      age: Number(payload.age),
      height_cm: Number(payload.height_cm),
      weight_kg: Number(payload.weight_kg),
      fitness_goal: payload.fitness_goal,
      diet_preference: payload.diet_preference,
      budget_amount: Number(payload.budget_amount),
      budget_period: payload.budget_period,
      location: payload.location,
      gym_type: payload.gym_type,
    },
  };
}

function switchView(viewId) {
  $$(".tab").forEach((item) => item.classList.toggle("active", item.dataset.view === viewId));
  $$(".rail-tab").forEach((item) => item.classList.toggle("active", item.dataset.view === viewId));
  $$(".view").forEach((item) => item.classList.toggle("active", item.id === viewId));
  closeNavDrawer();
}

$$(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    switchView(button.dataset.view);
  });
});

$$(".rail-tab").forEach((button) => {
  button.addEventListener("click", () => {
    switchView(button.dataset.view);
  });
});

function openNavDrawer() {
  $("#appShell").classList.add("nav-open");
  $("#navToggleBtn").setAttribute("aria-expanded", "true");
}

function closeNavDrawer() {
  $("#appShell")?.classList.remove("nav-open");
  $("#navToggleBtn")?.setAttribute("aria-expanded", "false");
}

$("#navToggleBtn").addEventListener("click", () => {
  if ($("#appShell").classList.contains("nav-open")) {
    closeNavDrawer();
    return;
  }
  openNavDrawer();
});

$("#navScrim").addEventListener("click", closeNavDrawer);

$("#todayWorkoutBtn").addEventListener("click", () => {
  selectedWorkoutDayIndex = state.current_workout_plan ? pickWorkoutDay(state.current_workout_plan.days) : null;
  switchView("workout");
  renderWorkout();
});

$$(".auth-tab").forEach((button) => {
  button.addEventListener("click", () => {
    setAuthMode(button.dataset.authMode);
  });
});

$("#signupContinueBtn").addEventListener("click", () => {
  $("#onboardingError").textContent = "";
  try {
    validateSignupAccountStep();
    syncSignupPreview();
    setSignupStep("profile");
  } catch (error) {
    $("#onboardingError").textContent = error.message;
  }
});

$("#signupBackBtn").addEventListener("click", () => {
  $("#onboardingError").textContent = "";
  setSignupStep("account");
});

$("#planBtn").addEventListener("click", async () => {
  await api(`/api/users/${state.user.id}/plans/weekly`, { method: "POST" });
  pendingAiWorkoutProposal = null;
  await refreshDashboardAndSession();
});

$("#reviewBtn").addEventListener("click", async () => {
  await api(`/api/users/${state.user.id}/weekly-review`, { method: "POST" });
  await refreshDashboardAndSession();
});

$("#profileForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#onboardingError").textContent = "";
  try {
    const session = await api("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(profilePayload(event.currentTarget)),
    });
    currentAccount = session.account;
    localStorage.setItem(AUTH_TOKEN_KEY, session.token);
    localStorage.setItem(ACTIVE_USER_KEY, String(session.profile.id));
    state = await api(`/api/users/${session.profile.id}/dashboard`);
    await loadActiveSession();
    await loadTrainerWorkspace();
    showApp();
    render();
  } catch (error) {
    setAuthMode("signup");
    $("#onboardingError").textContent = `Could not create account: ${error.message}`;
  }
});

$("#demoBtn").addEventListener("click", async () => {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  currentAccount = null;
  trainerWorkspace = null;
  const data = await api("/api/bootstrap");
  localStorage.setItem(ACTIVE_USER_KEY, String(data.user.id));
  state = data;
  await loadActiveSession();
  showApp();
  render();
});

$("#switchProfileBtn").addEventListener("click", () => {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(ACTIVE_USER_KEY);
  state = null;
  currentAccount = null;
  activeSession = null;
  trainerWorkspace = null;
  showOnboarding();
});

$("#loginBtn").addEventListener("click", async () => {
  $("#loginError").textContent = "";
  try {
    const session = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("input[name='login_email']").value,
        password: $("input[name='login_password']").value,
      }),
    });
    if (!session.profile) {
      $("#loginError").textContent = "Account has no profile yet.";
      return;
    }
    currentAccount = session.account;
    localStorage.setItem(AUTH_TOKEN_KEY, session.token);
    localStorage.setItem(ACTIVE_USER_KEY, String(session.profile.id));
    state = await api(`/api/users/${session.profile.id}/dashboard`);
    await loadActiveSession();
    await loadTrainerWorkspace();
    showApp();
    render();
  } catch (error) {
    setAuthMode("login");
    $("#loginError").textContent = error.message || "Invalid email or password.";
  }
});

$("#logForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  const sessionExerciseId = payload.session_exercise_id ? Number(payload.session_exercise_id) : null;
  if (activeSession && sessionExerciseId) {
    await api(`/api/sessions/${activeSession.id}/exercises/${sessionExerciseId}/sets`, {
      method: "POST",
      body: JSON.stringify({
        reps: Number(payload.reps_completed),
        weight_kg: Number(payload.weight_kg),
        perceived_effort: Number(payload.perceived_effort),
        completed: form.get("completed") === "on",
        pain_flag: form.get("pain_flag") === "on",
        notes: "",
      }),
    });
    $("input[name='session_exercise_id']").value = "";
    $("input[name='pain_flag']").checked = false;
    $("#selectedExercise").textContent = "";
    await refreshDashboardAndSession();
    return;
  }
  payload.sets_completed = Number(payload.sets_completed);
  payload.reps_completed = Number(payload.reps_completed);
  payload.weight_kg = Number(payload.weight_kg);
  payload.perceived_effort = Number(payload.perceived_effort);
  payload.planned_exercise_id = payload.planned_exercise_id ? Number(payload.planned_exercise_id) : null;
  delete payload.session_exercise_id;
  delete payload.pain_flag;
  payload.completed = form.get("completed") === "on";
  await api(`/api/users/${state.user.id}/workouts/logs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  $("input[name='planned_exercise_id']").value = "";
  $("#selectedExercise").textContent = "";
  await refreshDashboardAndSession();
});

$("#finishSessionBtn").addEventListener("click", async () => {
  if (activeSession) {
    try {
      const response = await api(`/api/sessions/${activeSession.id}/finish`, {
        method: "POST",
        body: JSON.stringify({ session_rpe: null, notes: "" }),
      });
      activeSession = response.session.status === "active" ? response.session : null;
      $("#finishSessionMessage").textContent = "Session finished. Dashboard updated from set-level logs.";
      await refreshDashboardAndSession();
    } catch (error) {
      $("#finishSessionMessage").textContent = error.message;
    }
    return;
  }
  const day = state.current_workout_plan.days[selectedWorkoutDayIndex - 1];
  const summary = summarizeDay(day);
  $("#finishSessionMessage").textContent = sessionMessage(summary);
});

$$(".feedback-buttons button").forEach((button) => {
  button.addEventListener("click", async () => {
    const result = await api(`/api/users/${state.user.id}/feedback`, {
      method: "POST",
      body: JSON.stringify({
        signal: button.dataset.signal,
        message: $("#feedbackMessage").value,
      }),
    });
    $("#feedbackResult").textContent = result.effect;
  });
});

$$("#equipmentQuickPicks button").forEach((button) => {
  button.addEventListener("click", () => {
    appendCommaValue($("#equipmentInput"), button.dataset.equipment);
    $("#aiPlanStatus").textContent = "Equipment added. Generate when the list matches your gym.";
  });
});

$$("#foodQuickPicks button").forEach((button) => {
  button.addEventListener("click", () => {
    appendCommaValue($("#dietFoodsInput"), button.dataset.food);
    $("#dietAiStatus").textContent = "Food added. Analyze when your pantry list is ready.";
  });
});

$("#generateAiPlanBtn").addEventListener("click", async () => {
  const equipmentText = $("#equipmentInput").value.trim();
  const button = $("#generateAiPlanBtn");
  if (!equipmentText) {
    $("#aiPlanStatus").textContent = "Add at least one equipment item first.";
    $("#equipmentInput").focus();
    return;
  }
  $("#aiPlanStatus").textContent = "Drafting a plan from your equipment...";
  setButtonLoading(button, true, "Generating...");
  try {
    pendingAiWorkoutProposal = await api(`/api/users/${state.user.id}/ai/workout-proposal`, {
      method: "POST",
      body: JSON.stringify({ equipment_text: equipmentText }),
    });
    renderAiWorkoutProposal();
  } catch (error) {
    $("#aiPlanStatus").textContent = error.message;
  } finally {
    setButtonLoading(button, false);
  }
});

async function acceptAiPlan() {
  const button = $("#acceptAiPlanBtn");
  $("#aiPlanStatus").textContent = "Applying this plan...";
  setButtonLoading(button, true, "Applying...");
  try {
    await api(`/api/users/${state.user.id}/ai/workout-proposal/accept`, {
      method: "POST",
      body: JSON.stringify(pendingAiWorkoutProposal.proposal),
    });
    pendingAiWorkoutProposal = null;
    selectedWorkoutDayIndex = null;
    await refreshDashboardAndSession();
    $("#aiPlanStatus").textContent = "Accepted. Your session flow is now using this plan.";
  } catch (error) {
    $("#aiPlanStatus").textContent = error.message;
    setButtonLoading(button, false);
  }
}

$("#exerciseQuestionForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  if (!$("#exerciseQuestionName").value.trim() || !$("#exerciseQuestionInput").value.trim()) {
    $("#exerciseAnswer").classList.remove("hidden");
    $("#exerciseAnswer").innerHTML = "<p class='error'>Pick an exercise and ask a specific question.</p>";
    return;
  }
  const result = $("#exerciseAnswer");
  result.classList.remove("hidden");
  result.innerHTML = "<p class='muted'>Thinking through that lift...</p>";
  setButtonLoading(button, true, "Asking...");
  try {
    const answer = await api(`/api/users/${state.user.id}/ai/exercise-advice`, {
      method: "POST",
      body: JSON.stringify({
        exercise_name: $("#exerciseQuestionName").value,
        question: $("#exerciseQuestionInput").value,
      }),
    });
    result.innerHTML = `<p>${escapeHtml(answer.answer)}</p>`;
  } catch (error) {
    result.innerHTML = `<p class="error">${error.message}</p>`;
  } finally {
    setButtonLoading(button, false);
  }
});

$("#analyzeDietBtn").addEventListener("click", async () => {
  const button = $("#analyzeDietBtn");
  if (!$("#dietFoodsInput").value.trim()) {
    $("#dietAiStatus").textContent = "Add the foods you already have first.";
    $("#dietFoodsInput").focus();
    return;
  }
  const result = $("#dietAiResult");
  result.classList.remove("hidden");
  $("#dietAiStatus").textContent = "Reviewing your current foods...";
  result.innerHTML = "<p class='muted'>Checking calories, protein, and tradeoffs...</p>";
  setButtonLoading(button, true, "Analyzing...");
  try {
    const response = await api(`/api/users/${state.user.id}/ai/diet-analysis`, {
      method: "POST",
      body: JSON.stringify({
        foods_text: $("#dietFoodsInput").value,
        question: $("#dietQuestionInput").value || "How can I make this work well for my goal?",
      }),
    });
    const analysis = response.analysis;
    $("#dietAiStatus").textContent = response.enabled ? "AI used your pantry and goal." : "Fallback analysis used because AI is not configured.";
    result.innerHTML = `
      <div class="diet-ai-summary">
        <strong>${analysis.estimated_calories} kcal | ${analysis.estimated_protein_g}g protein</strong>
        <p>${escapeHtml(analysis.summary)}</p>
      </div>
      <div class="diet-ai-columns">
        <div>
          <h4>Benefits</h4>
          <ul>${analysis.benefits.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
        <div>
          <h4>Risks</h4>
          <ul>${analysis.risks.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
      </div>
      <div>
        <h4>Suggested use</h4>
        <ul>${analysis.suggested_meals.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
    `;
  } catch (error) {
    $("#dietAiStatus").textContent = error.message;
    result.innerHTML = `<p class="error">${error.message}</p>`;
  } finally {
    setButtonLoading(button, false);
  }
});

load().catch((error) => {
  document.body.innerHTML = `<pre>${error.message}</pre>`;
});
