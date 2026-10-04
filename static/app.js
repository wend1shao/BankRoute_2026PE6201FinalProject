const $ = (selector) => document.querySelector(selector);
const pct = (value, digits = 1) => `${(Number(value || 0) * 100).toFixed(digits)}%`;

const state = { health: null, cases: [] };

async function getJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
  return data;
}

async function initialise() {
  const [health, cases, metrics] = await Promise.all([
    getJson("/api/health"),
    getJson("/api/demo-cases"),
    getJson("/api/metrics").catch(() => ({ available: false })),
  ]);
  state.health = health;
  state.cases = cases;

  $("#system-dot").classList.toggle("online", health.models_ready);
  $("#system-status").textContent = health.models_ready ? "Models ready" : "Training required";
  const llm = $("#allow-llm");
  llm.disabled = !health.openrouter_key_available;
  $("#llm-status").textContent = health.openrouter_key_available
    ? `${health.openrouter_model} available · ambiguous cases only`
    : "API key unavailable · local model remains fully functional";

  const chips = $("#demo-cases");
  cases.forEach((item) => {
    const button = document.createElement("button");
    button.className = "sample-chip";
    button.type = "button";
    button.textContent = item.label;
    button.addEventListener("click", () => {
      $("#message").value = item.message;
      updateCount();
      $("#message").focus();
    });
    chips.appendChild(button);
  });

  if (metrics.available) {
    $("#selective-accuracy").textContent = pct(metrics.guarded_router.selective_accuracy);
    $("#macro-f1").textContent = metrics.tfidf_logistic_closed_set.macro_f1.toFixed(3);
    $("#oos-safe").textContent = pct(metrics.guarded_router.out_of_scope_safe_escalation);
    $("#coverage").textContent = pct(metrics.guarded_router.in_scope_coverage);
    $("#test-rows").textContent = metrics.dataset.official_test_rows.toLocaleString();
  }
}

function updateCount() {
  $("#char-count").textContent = $("#message").value.length;
}

function guardrailItem(title, detail, warning = false) {
  return `<div class="guardrail-item ${warning ? "warn" : ""}">
    <i>${warning ? "!" : "✓"}</i><div><strong>${title}</strong><small>${detail}</small></div>
  </div>`;
}

function renderResult(data) {
  const review = data.human_review;
  $("#result-section").classList.remove("hidden");
  $("#decision-icon").classList.toggle("review", review);
  $("#decision-kicker").textContent = review ? "HUMAN REVIEW REQUIRED" : "ROUTING DECISION";
  $("#decision-name").textContent = data.display_name;
  $("#decision-explanation").textContent = data.explanation;
  $("#route-to").textContent = data.route_to;
  $("#review-badge").textContent = review ? "Manual confirmation" : "Auto-route eligible";
  $("#latency").textContent = `${data.latency_ms.toFixed(1)} ms${data.llm_used ? " + LLM" : " local"}`;
  $("#confidence").textContent = pct(data.confidence, 0);
  $("#scope-confidence").textContent = `${pct(data.scope_probability)} in supported scope`;
  $("#gauge-fill").parentElement.style.background = `conic-gradient(var(--teal) ${data.confidence * 360}deg, #e7edef 0)`;

  $("#candidate-bars").innerHTML = data.candidates.map((candidate) => `
    <div class="candidate-row">
      <span title="${candidate.intent}">${candidate.display_name}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${candidate.probability * 100}%"></div></div>
      <strong>${pct(candidate.probability, 0)}</strong>
    </div>`).join("");

  const flags = new Set(data.safety_flags || []);
  const guards = [
    guardrailItem("Closed intent vocabulary", "Only ten approved labels and fixed queues are available."),
    guardrailItem(
      data.pii_redacted ? "PII redacted" : "PII scan passed",
      data.pii_redacted ? `External processing sees: ${data.redacted_message}` : "No card, account, email or phone pattern detected.",
      data.pii_redacted,
    ),
    guardrailItem(
      flags.has("prompt_injection_detected") ? "Prompt injection blocked" : "Injection scan passed",
      flags.has("prompt_injection_detected") ? "External-model use was blocked and the case was escalated." : "No instruction override pattern detected.",
      flags.has("prompt_injection_detected"),
    ),
    guardrailItem(
      review ? "Abstention activated" : "Decision thresholds passed",
      review ? "The system declined to auto-route and handed control to an agent." : "Scope, confidence and top-two margin passed validation thresholds.",
      review,
    ),
  ];
  $("#guardrail-list").innerHTML = guards.join("");

  $("#tool-trace").innerHTML = data.tool_trace.map((step, index) => `
    <div class="trace-step"><span>${String(index + 1).padStart(2, "0")} · ${step.status}</span><strong>${step.tool.replaceAll("_", " ")}</strong><p>${step.detail}</p></div>
  `).join("");
  $("#result-section").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function route() {
  const button = $("#route-button");
  const message = $("#message").value.trim();
  if (message.length < 3) {
    $("#message").focus();
    $("#message").setAttribute("placeholder", "Please enter at least three characters.");
    return;
  }
  button.disabled = true;
  button.querySelector("span").textContent = "Analysing…";
  try {
    const data = await getJson("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, allow_llm: $("#allow-llm").checked }),
    });
    renderResult(data);
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "Analyse & route";
  }
}

$("#message").addEventListener("input", updateCount);
$("#message").addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") route();
});
$("#route-button").addEventListener("click", route);
initialise().catch((error) => {
  $("#system-status").textContent = "System unavailable";
  console.error(error);
});

