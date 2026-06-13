const STORAGE_KEY = "ia_session_id";
const { normalizeProvider, normalizeModelInput, resolvedModel, writeStatusCache, clearStatusCache, readStatusCache } =
  window.PortkeyConnect || {};

let sessionId = localStorage.getItem(STORAGE_KEY) || crypto.randomUUID();
localStorage.setItem(STORAGE_KEY, sessionId);

const wizardEl = document.getElementById("pk-wizard");
const badgeEl = document.getElementById("pk-connected-badge");
const savedHintEl = document.getElementById("pk-saved-hint");
const apiKeyInput = document.getElementById("pk-api-key");
const providerInput = document.getElementById("pk-provider");
const modelInput = document.getElementById("pk-model");
const modelPreviewEl = document.getElementById("pk-model-preview");
const resultBox = document.getElementById("pk-result");
const resultTitle = document.getElementById("pk-result-title");
const resultDetail = document.getElementById("pk-result-detail");
const resultAction = document.getElementById("pk-result-action");
const testOutput = document.getElementById("pk-test-output");
const setupOut = document.getElementById("pk-setup-output");
const publicBaseInput = document.getElementById("pk-public-base");
const openKeysBtn = document.getElementById("pk-open-keys");
const connectBtn = document.getElementById("pk-connect-btn");

let hasSavedKey = false;

function updateModelPreview() {
  if (!modelPreviewEl) return;
  modelPreviewEl.textContent = resolvedModel(
    providerInput?.value || "iaagent1",
    modelInput?.value || "babbage-002"
  );
}

function setBadge(state) {
  if (!badgeEl) return;
  const labels = {
    verified: ["Connected & tested", "ok"],
    saved: ["Key saved", "ok"],
    needs_provider: ["Key saved — add provider", "warn"],
    verify_failed: ["Key saved — fix provider/model", "warn"],
    disconnected: ["Not connected", ""],
  };
  const [text, kind] = labels[state] || labels.disconnected;
  badgeEl.textContent = text;
  badgeEl.className = `pk-badge${kind ? ` ${kind}` : ""}`;
}

function showResult({ title, detail, action, reply, kind = "" }) {
  if (!resultBox) return;
  resultBox.hidden = false;
  resultBox.className = `pk-result${kind ? ` ${kind}` : ""}`;
  if (resultTitle) resultTitle.textContent = title || "";
  if (resultDetail) resultDetail.textContent = detail || "";
  if (resultAction) {
    if (action?.action_url) {
      resultAction.hidden = false;
      resultAction.href = action.action_url;
      resultAction.textContent = action.action_label || "Open Portkey";
    } else {
      resultAction.hidden = true;
    }
  }
  if (testOutput) {
    if (reply) {
      testOutput.hidden = false;
      testOutput.textContent = `Test reply: ${reply}`;
    } else {
      testOutput.hidden = true;
      testOutput.textContent = "";
    }
  }
  resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function clearResult() {
  if (resultBox) resultBox.hidden = true;
}

async function fetchJson(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok && data.ok !== true) {
    const detail = data.detail;
    const message =
      (detail && typeof detail === "object" ? detail.message : detail) ||
      data.message ||
      `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

function renderWizard(steps, links) {
  if (!wizardEl || !Array.isArray(steps)) return;
  wizardEl.innerHTML = steps
    .map((step) => {
      const action =
        step.action_url && step.step !== "3"
          ? `<a class="pk-btn ghost pk-open-link" href="${step.action_url}" target="_blank" rel="noopener">${step.action_label}</a>`
          : "";
      return `<li class="pk-wizard-step" data-step="${step.step}">
        <span class="pk-step-num">${step.step}</span>
        <div>
          <strong>${step.title}</strong>
          <p>${step.detail}</p>
          ${action}
        </div>
      </li>`;
    })
    .join("");
  if (openKeysBtn && links?.api_keys) openKeysBtn.href = links.api_keys;
}

function setSavedKeyHint(visible) {
  hasSavedKey = visible;
  if (savedHintEl) savedHintEl.hidden = !visible;
  if (apiKeyInput) {
    apiKeyInput.placeholder = visible
      ? "Key saved — leave blank to re-test, or paste a new key"
      : "Paste from Portkey → API Keys → Reveal";
  }
}

function cacheConnection(data) {
  writeStatusCache({
    verified: data.connection_state === "verified",
    connection_state: data.connection_state,
    provider_slug: data.provider_slug,
    model_suffix: data.model_suffix,
    resolved_model: data.resolved_model,
    has_saved_key: data.connection_state !== "disconnected",
  });
}

function redirectToMain() {
  showResult({
    title: "Success — redirecting to ReviewRun",
    detail: "Portkey is connected. ReviewRun is now in governance + build mode.",
    kind: "ok",
  });
  window.setTimeout(() => {
    window.location.href = "/?portkey=connected";
  }, 1400);
}

async function refreshStatus() {
  const data = await fetchJson(
    `/api/portkey/plane-b/status?session_id=${encodeURIComponent(sessionId)}`
  );
  renderWizard(data.wizard || [], data.portkey_links || {});
  setBadge(data.connection_state || (data.connected ? "saved" : "disconnected"));
  setSavedKeyHint(Boolean(data.has_saved_key || data.connected));

  const cache = readStatusCache();
  if (providerInput && !providerInput.value) {
    providerInput.value = data.provider_slug || cache.provider_slug || "";
  }
  if (modelInput && !modelInput.value) {
    modelInput.value = data.model_suffix || cache.model_suffix || "";
  }
  updateModelPreview();

  if (data.connection_state === "verified") {
    cacheConnection(data);
    showResult({
      title: "Already connected",
      detail: "Your Portkey gateway is ready. You can re-test or return to ReviewRun.",
      kind: "ok",
    });
  }
  return data;
}

async function connectPortkey() {
  const apiKey = (apiKeyInput?.value || "").trim();
  const normalized = normalizeModelInput(providerInput?.value, modelInput?.value);
  const provider = normalized.providerSlug;
  const model = normalized.modelSuffix;

  if (providerInput && normalized.providerSlug !== normalizeProvider(providerInput.value)) {
    providerInput.value = normalized.providerSlug;
  }
  if (modelInput && normalized.modelSuffix !== (modelInput.value || "").trim()) {
    modelInput.value = normalized.modelSuffix;
  }
  updateModelPreview();

  if (!apiKey && !hasSavedKey) {
    showResult({
      title: "Paste your Portkey API key",
      detail: "Open API Keys in Portkey, click Reveal, copy, and paste here.",
      action: { action_label: "Open API Keys", action_url: openKeysBtn?.href || "https://app.portkey.ai/api-keys" },
    });
    return;
  }
  if (!provider) {
    showResult({
      title: "Enter your provider slug",
      detail: "In Portkey open your provider (e.g. iaagent1) and copy the Slug without the @.",
      action: { action_label: "Open Model Catalog", action_url: "https://app.portkey.ai/model-catalog" },
    });
    return;
  }
  if (!model) {
    showResult({
      title: "Enter the model name",
      detail: "Use the model shown on Portkey → API Setup & Code (e.g. babbage-002).",
    });
    return;
  }

  if (connectBtn) {
    connectBtn.disabled = true;
    connectBtn.textContent = "Testing connection…";
  }
  showResult({
    title: "Working…",
    detail: apiKey
      ? "Saving your key and sending a test message through Portkey."
      : "Re-testing with your saved key.",
  });

  try {
    const data = await fetchJson("/api/portkey/plane-b/connect", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        api_key: apiKey,
        provider,
        model,
        run_test: true,
      }),
    });
    if (apiKey && apiKeyInput) apiKeyInput.value = "";
    cacheConnection(data);
    setSavedKeyHint(true);
    setBadge(data.connection_state || "saved");

    if (data.connection_state === "verified") {
      showResult({
        title: "Connected",
        detail: data.message || "Portkey gateway is working.",
        reply: data.test_reply || data.verification?.sample_reply,
        kind: "ok",
      });
      redirectToMain();
      return;
    }
    if (data.connection_state === "needs_provider") {
      showResult({
        title: "Almost there",
        detail: data.message,
        action: { action_label: "Open Model Catalog", action_url: "https://app.portkey.ai/model-catalog" },
      });
      return;
    }
    showResult({
      title: data.next_action?.title || "Check provider and model",
      detail: [
        data.next_action?.detail || data.message,
        data.verification?.detail ? `Portkey: ${data.verification.detail}` : "",
        "Your key is saved — fix slug/model above and click Save & test again (no re-paste needed).",
      ]
        .filter(Boolean)
        .join(" "),
      action: data.next_action,
    });
  } catch (err) {
    setBadge(hasSavedKey ? "verify_failed" : "disconnected");
    showResult({
      title: "Connection failed",
      detail: String(err.message || err),
      action: { action_label: "Open API Keys", action_url: openKeysBtn?.href || "https://app.portkey.ai/api-keys" },
    });
  } finally {
    if (connectBtn) {
      connectBtn.disabled = false;
      connectBtn.textContent = "Save & test connection";
    }
  }
}

async function disconnectPortkey() {
  await fetchJson("/api/portkey/plane-b/disconnect", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
  clearStatusCache();
  setBadge("disconnected");
  setSavedKeyHint(false);
  clearResult();
  if (setupOut) setupOut.textContent = "";
}

async function loadGuardrailSetup() {
  const publicBaseUrl = (publicBaseInput?.value || window.location.origin).trim();
  const data = await fetchJson(
    `/api/portkey/plane-b/guardrail-setup?session_id=${encodeURIComponent(sessionId)}&public_base_url=${encodeURIComponent(publicBaseUrl)}&format=markdown`
  );
  const text = data.markdown || JSON.stringify(data.setup, null, 2);
  if (setupOut) setupOut.textContent = text;
  try {
    await navigator.clipboard.writeText(text);
    showResult({ title: "Copied", detail: "Guardrail setup sheet copied to clipboard." });
  } catch {
    showResult({ title: "Ready", detail: "Guardrail setup sheet is in the Advanced section below." });
  }
}

providerInput?.addEventListener("input", updateModelPreview);
modelInput?.addEventListener("input", updateModelPreview);
connectBtn?.addEventListener("click", connectPortkey);
document.getElementById("pk-disconnect-btn")?.addEventListener("click", disconnectPortkey);
document.getElementById("pk-setup-btn")?.addEventListener("click", loadGuardrailSetup);

if (publicBaseInput && !publicBaseInput.value) {
  publicBaseInput.value = window.location.origin;
}
const cache = readStatusCache();
if (providerInput && !providerInput.value) {
  providerInput.value = cache.provider_slug || localStorage.getItem("ia_portkey_provider_slug") || "";
}
if (modelInput && !modelInput.value) {
  modelInput.value = cache.model_suffix || localStorage.getItem("ia_portkey_model_suffix") || "";
}
updateModelPreview();

void refreshStatus().catch(() => {
  renderWizard(
    [
      {
        step: "1",
        title: "Add an AI provider in Portkey",
        detail: "Model Catalog → add OpenAI (or other). Note the slug, e.g. iaagent1.",
        action_label: "Open Model Catalog",
        action_url: "https://app.portkey.ai/model-catalog",
      },
      {
        step: "2",
        title: "Copy your Portkey API key",
        detail: "API Keys → default key → Reveal → copy.",
        action_label: "Open API Keys",
        action_url: "https://app.portkey.ai/api-keys",
      },
      {
        step: "3",
        title: "Paste here — we test and send you back to ReviewRun",
        detail: "Use the slug and model from your provider's API Setup tab.",
        action_label: "",
        action_url: "",
      },
    ],
    { api_keys: "https://app.portkey.ai/api-keys", model_catalog: "https://app.portkey.ai/model-catalog" }
  );
});
