const API_BASE = window.location.origin;
const PREDICT_ENDPOINT = `${API_BASE}/predict-vancomycin`;

const THERAPEUTIC_MIN = 10;
const THERAPEUTIC_MAX = 20;
const RANGE_DISPLAY_MAX = 30;

const form = document.getElementById("vanco-form");
const resultCard = document.getElementById("result-card");
const resultValue = document.getElementById("result-value");
const statusBadge = document.getElementById("status-badge");
const rangeMarker = document.getElementById("range-marker");
const errorBlock = document.getElementById("error-block");
const resultContent = document.getElementById("result-content");
const submitBtn = document.getElementById("submit-btn");

function parseFloatField(value, label) {
  const trimmed = (value ?? "").trim();
  if (!trimmed) {
    throw new Error(`${label} is required.`);
  }
  const parsed = parseFloat(trimmed);
  if (Number.isNaN(parsed)) {
    throw new Error(`${label} must be a valid number.`);
  }
  return parsed;
}

function parseTextField(value, label) {
  const trimmed = (value ?? "").trim();
  if (!trimmed) {
    throw new Error(`${label} is required.`);
  }
  return trimmed;
}

function collectFormData() {
  const data = new FormData(form);

  const age = parseFloatField(data.get("age"), "Age");
  const creatinine = parseFloatField(data.get("creatinine"), "Creatinine");
  const bun = parseFloatField(data.get("bun"), "BUN");
  const admissionweight = parseFloatField(data.get("admissionweight"), "Admission weight");
  const dose_amount_mg = parseFloatField(data.get("dose_amount_mg"), "Dose amount");
  const dose_offset = parseFloatField(data.get("dose_offset"), "Dose offset");

  if (age <= 0 || age > 120) throw new Error("Age must be between 1 and 120.");
  if (creatinine <= 0) throw new Error("Creatinine must be greater than 0.");
  if (bun < 0) throw new Error("BUN cannot be negative.");
  if (admissionweight <= 0) throw new Error("Admission weight must be greater than 0.");
  if (dose_amount_mg <= 0) throw new Error("Dose amount must be greater than 0.");

  return {
    age,
    gender: parseTextField(data.get("gender"), "Gender"),
    admissionweight,
    creatinine,
    bun,
    unittype: parseTextField(data.get("unittype"), "Unit type"),
    level_type: parseTextField(data.get("level_type"), "Level type"),
    dose_amount_mg,
    dose_raw: parseTextField(data.get("dose_raw"), "Dose raw"),
    dose_route: parseTextField(data.get("dose_route"), "Dose route"),
    dose_frequency: parseTextField(data.get("dose_frequency"), "Dose frequency"),
    dose_drugname: parseTextField(data.get("dose_drugname"), "Dose drug name"),
    dose_offset,
    dose_parse_status: parseTextField(data.get("dose_parse_status"), "Dose parse status"),
  };
}

function getTherapeuticStatus(level) {
  if (level < THERAPEUTIC_MIN) {
    return { key: "subtherapeutic", label: "Subtherapeutic" };
  }
  if (level <= THERAPEUTIC_MAX) {
    return { key: "target", label: "Target Range" };
  }
  return { key: "high", label: "High" };
}

function showError(message) {
  resultCard.classList.add("visible", "error");
  errorBlock.hidden = false;
  resultContent.hidden = true;
  document.getElementById("error-text").textContent = message;
}

function showResult(level) {
  resultCard.classList.remove("error");
  errorBlock.hidden = true;
  resultContent.hidden = false;

  resultValue.textContent = level.toFixed(2);

  const status = getTherapeuticStatus(level);
  statusBadge.className = `status-badge ${status.key}`;
  statusBadge.innerHTML = `<span class="status-dot"></span>${status.label}`;

  const clamped = Math.max(0, Math.min(level, RANGE_DISPLAY_MAX));
  const percent = (clamped / RANGE_DISPLAY_MAX) * 100;
  rangeMarker.style.left = `${percent}%`;

  resultCard.classList.add("visible");
  resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function parseApiError(response, body) {
  if (response.status === 422 && body.detail) {
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((err) => {
          const field = err.loc ? err.loc.slice(1).join(".") : "field";
          return `${field}: ${err.msg}`;
        })
        .join(" ");
    }
    return typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  }

  if (body.detail) {
    return typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  }

  return `Request failed with status ${response.status}. Please try again.`;
}

function setLoading(loading) {
  submitBtn.disabled = loading;
  submitBtn.classList.toggle("loading", loading);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);

  try {
    const payload = collectFormData();

    const response = await fetch(PREDICT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let body = {};
    try {
      body = await response.json();
    } catch {
      /* non-JSON response */
    }

    if (!response.ok) {
      showError(parseApiError(response, body));
      return;
    }

    if (body.success && typeof body.predicted_vancomycin_level === "number") {
      showResult(body.predicted_vancomycin_level);
    } else {
      showError("Unexpected response from server. Please try again.");
    }
  } catch (err) {
    if (err instanceof TypeError && err.message.includes("fetch")) {
      showError(
        "Unable to reach the API. Ensure the FastAPI server is running and you are accessing this page via /ui."
      );
    } else {
      showError(err.message || "An unexpected error occurred.");
    }
  } finally {
    setLoading(false);
  }
});
