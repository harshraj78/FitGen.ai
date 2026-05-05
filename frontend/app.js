let state = null;
const ACTIVE_USER_KEY = "fitgen-active-user-id";
const AUTH_TOKEN_KEY = "fitgen-auth-token";
let selectedWorkoutDayIndex = null;

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
      const profileId = activeUserId || session.profile?.id;
      if (!profileId) {
        showOnboarding("Account found, but no profile exists yet.");
        return;
      }
      localStorage.setItem(ACTIVE_USER_KEY, String(profileId));
      state = await api(`/api/users/${profileId}/dashboard`);
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
    showApp();
    render();
  } catch (error) {
    localStorage.removeItem(ACTIVE_USER_KEY);
    showOnboarding("Saved profile was not found. Create a new one or load the demo profile.");
  }
}

function render() {
  renderProfile();
  renderStats();
  renderWorkout();
  renderDiet();
  renderReview();
  renderRecentLogs();
  drawVolumeChart();
  $("#exportLink").href = `/api/users/${state.user.id}/report/export`;
}

function showOnboarding(message = "") {
  $("#onboarding").classList.add("active");
  $("#onboardingError").textContent = message;
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

function renderWorkout() {
  const plan = state.current_workout_plan;
  if (!plan) {
    $("#daySelector").innerHTML = "<p>No workout plan yet.</p>";
    $("#sessionSummary").innerHTML = "";
    $("#selectedDayPlan").innerHTML = "";
    $("#finishSessionMessage").textContent = "";
    return;
  }
  if (!selectedWorkoutDayIndex || !plan.days.some((day, index) => index + 1 === selectedWorkoutDayIndex)) {
    selectedWorkoutDayIndex = pickWorkoutDay(plan.days);
  }
  const selectedDay = plan.days[selectedWorkoutDayIndex - 1];
  const dayStatuses = summarizeDay(selectedDay);
  $("#workoutTitle").textContent = plan.title;
  $("#sessionMeta").textContent = `${selectedDay.day} | ${selectedDay.exercises.length} planned exercises`;
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
        <span>${day.focus}</span>
      </button>
    `,
    )
    .join("");
  $("#selectedDayPlan").innerHTML = `
    <div class="session-day-head">
      <div>
        <h3>${selectedDay.day}</h3>
        <p class="muted">${selectedDay.focus}</p>
      </div>
      <span class="session-badge">${selectedDay.exercises.length} lifts queued</span>
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
  $("input[name='performed_on']").valueAsDate = new Date();
}

function renderDiet() {
  const diet = state.current_diet_plan;
  if (!diet) {
    $("#dietPlan").innerHTML = "<p>No diet plan yet.</p>";
    return;
  }
  $("#dietPlan").innerHTML = diet.meals
    .map(
      (meal) => `
      <article class="meal">
        <h3>${meal.name}</h3>
        <ul>${meal.items.map((item) => `<li>${item}</li>`).join("")}</ul>
        <p>${meal.calories} kcal | ${meal.protein_g}g protein</p>
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

function labelExerciseStatus(status) {
  return { completed: "Done", skipped: "Skipped", pending: "Pending" }[status] || "Pending";
}

function pickWorkoutDay(days) {
  const today = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][new Date().getDay()];
  const matchIndex = days.findIndex((day) => day.day === today);
  return matchIndex >= 0 ? matchIndex + 1 : 1;
}

function loadExerciseIntoLog(exerciseId, exerciseName, targetWeight) {
  $("input[name='planned_exercise_id']").value = exerciseId;
  $("input[name='exercise_name']").value = exerciseName;
  $("input[name='weight_kg']").value = Number(targetWeight || 0);
  $("#selectedExercise").textContent = `Logging planned exercise: ${exerciseName}`;
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

async function markExerciseSkipped(exerciseId, exerciseName) {
  await api(`/api/users/${state.user.id}/workouts/logs`, {
    method: "POST",
    body: JSON.stringify({
      planned_exercise_id: Number(exerciseId),
      exercise_name: exerciseName,
      performed_on: state.current_workout_plan.week_start,
      sets_completed: 0,
      reps_completed: 0,
      weight_kg: 0,
      completed: false,
      perceived_effort: 3,
    }),
  });
  state = await api(`/api/users/${state.user.id}/dashboard`);
  render();
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

$$(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    $$(".tab").forEach((item) => item.classList.remove("active"));
    $$(".view").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    $(`#${button.dataset.view}`).classList.add("active");
  });
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
  state = await api(`/api/users/${state.user.id}/dashboard`);
  render();
});

$("#reviewBtn").addEventListener("click", async () => {
  await api(`/api/users/${state.user.id}/weekly-review`, { method: "POST" });
  state = await api(`/api/users/${state.user.id}/dashboard`);
  render();
});

$("#profileForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#onboardingError").textContent = "";
  try {
    const session = await api("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(profilePayload(event.currentTarget)),
    });
    localStorage.setItem(AUTH_TOKEN_KEY, session.token);
    localStorage.setItem(ACTIVE_USER_KEY, String(session.profile.id));
    state = await api(`/api/users/${session.profile.id}/dashboard`);
    showApp();
    render();
  } catch (error) {
    setAuthMode("signup");
    $("#onboardingError").textContent = `Could not create account: ${error.message}`;
  }
});

$("#demoBtn").addEventListener("click", async () => {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  const data = await api("/api/bootstrap");
  localStorage.setItem(ACTIVE_USER_KEY, String(data.user.id));
  state = data;
  showApp();
  render();
});

$("#switchProfileBtn").addEventListener("click", () => {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(ACTIVE_USER_KEY);
  state = null;
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
    localStorage.setItem(AUTH_TOKEN_KEY, session.token);
    localStorage.setItem(ACTIVE_USER_KEY, String(session.profile.id));
    state = await api(`/api/users/${session.profile.id}/dashboard`);
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
  payload.sets_completed = Number(payload.sets_completed);
  payload.reps_completed = Number(payload.reps_completed);
  payload.weight_kg = Number(payload.weight_kg);
  payload.perceived_effort = Number(payload.perceived_effort);
  payload.planned_exercise_id = payload.planned_exercise_id ? Number(payload.planned_exercise_id) : null;
  payload.completed = form.get("completed") === "on";
  await api(`/api/users/${state.user.id}/workouts/logs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  $("input[name='planned_exercise_id']").value = "";
  $("#selectedExercise").textContent = "";
  state = await api(`/api/users/${state.user.id}/dashboard`);
  render();
});

$("#finishSessionBtn").addEventListener("click", () => {
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

load().catch((error) => {
  document.body.innerHTML = `<pre>${error.message}</pre>`;
});
