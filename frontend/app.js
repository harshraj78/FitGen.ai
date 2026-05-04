let state = null;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function load() {
  state = await api("/api/bootstrap");
  render();
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
  $("#calorieTarget").textContent = diet.calories || 0;
  $("#proteinTarget").textContent = `${diet.protein_g || 0}g`;
}

function renderWorkout() {
  const plan = state.current_workout_plan;
  if (!plan) {
    $("#workoutPlan").innerHTML = "<p>No workout plan yet.</p>";
    return;
  }
  $("#workoutPlan").innerHTML = plan.days
    .map(
      (day) => `
      <article class="day">
        <h3>${day.day} | ${day.focus}</h3>
        ${day.exercises
          .map(
            (exercise) => `
            <div class="exercise">
              <strong>${exercise.name}</strong>
              <span>${exercise.sets} sets x ${exercise.target_reps} reps | ${exercise.target_weight_kg || "bodyweight"} kg</span>
              <span>${exercise.equipment} | ${exercise.notes}</span>
            </div>
          `,
          )
          .join("")}
      </article>
    `,
    )
    .join("");

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

$$(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    $$(".tab").forEach((item) => item.classList.remove("active"));
    $$(".view").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    $(`#${button.dataset.view}`).classList.add("active");
  });
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

$("#logForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.sets_completed = Number(payload.sets_completed);
  payload.reps_completed = Number(payload.reps_completed);
  payload.weight_kg = Number(payload.weight_kg);
  payload.perceived_effort = Number(payload.perceived_effort);
  payload.completed = form.get("completed") === "on";
  await api(`/api/users/${state.user.id}/workouts/logs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state = await api(`/api/users/${state.user.id}/dashboard`);
  render();
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
