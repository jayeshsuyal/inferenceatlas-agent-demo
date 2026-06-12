/** Shared Portkey Plane B local cache + main-page sync helpers. */
(function initPortkeyConnectShared(global) {
  const PROVIDER_KEY = "ia_portkey_provider_slug";
  const MODEL_KEY = "ia_portkey_model_suffix";
  const STATUS_KEY = "ia_portkey_status_cache";

  function normalizeProvider(value) {
    return String(value || "").trim().replace(/^@+/, "");
  }

  function resolvedModel(provider, modelSuffix) {
    const slug = normalizeProvider(provider) || "your-provider";
    const model = String(modelSuffix || "gpt-4o-mini").trim().replace(/^@+/, "");
    return `@${slug}/${model}`;
  }

  function readStatusCache() {
    try {
      return JSON.parse(localStorage.getItem(STATUS_KEY) || "{}");
    } catch {
      return {};
    }
  }

  function writeStatusCache(patch) {
    const next = { ...readStatusCache(), ...patch, updated_at: new Date().toISOString() };
    localStorage.setItem(STATUS_KEY, JSON.stringify(next));
    if (patch.provider_slug) localStorage.setItem(PROVIDER_KEY, patch.provider_slug);
    if (patch.model_suffix) localStorage.setItem(MODEL_KEY, patch.model_suffix);
    return next;
  }

  function clearStatusCache() {
    localStorage.removeItem(STATUS_KEY);
    localStorage.removeItem(PROVIDER_KEY);
    localStorage.removeItem(MODEL_KEY);
  }

  function applyStatusToDocument(status) {
    const verified = Boolean(status?.verified || status?.connection_state === "verified");
    document.body.dataset.portkeyMode = verified ? "governance-build" : "governance";
    document.body.dataset.portkeyConnected = verified ? "true" : "false";
    return verified;
  }

  async function fetchPortkeyStatus(sessionId) {
    const res = await fetch(
      `/api/portkey/plane-b/status?session_id=${encodeURIComponent(sessionId)}`
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Portkey status failed");
    return data;
  }

  async function syncPortkeyUi(sessionId) {
    let status;
    try {
      status = await fetchPortkeyStatus(sessionId);
    } catch {
      status = readStatusCache();
    }
    const verified = applyStatusToDocument(status);
    if (status?.provider_slug || status?.model_suffix) {
      writeStatusCache({
        verified,
        connection_state: status.connection_state,
        provider_slug: status.provider_slug || readStatusCache().provider_slug,
        model_suffix: status.model_suffix || readStatusCache().model_suffix,
        resolved_model: status.resolved_model,
        has_saved_key: status.has_saved_key ?? status.connected,
      });
    }
    updatePortkeyNavButton(verified, status);
    updateReviewRunBuildMode(verified, status);
    updatePortkeyStackPill(verified, status);
    return status;
  }

  function updatePortkeyNavButton(verified, status) {
    const btn = document.getElementById("btn-portkey-connect");
    if (!btn) return;
    if (verified) {
      btn.textContent = "Portkey connected";
      btn.classList.add("portkey-connected");
      btn.title = `Gateway: ${status?.resolved_model || resolvedModel(status?.provider_slug, status?.model_suffix)}`;
    } else if (status?.has_saved_key || status?.connected) {
      btn.textContent = "Finish Portkey setup";
      btn.classList.remove("portkey-connected");
      btn.classList.add("portkey-pending");
      btn.title = "Key saved — finish provider setup";
    } else {
      btn.textContent = "Connect PortKey";
      btn.classList.remove("portkey-connected", "portkey-pending");
      btn.title = "Connect your Portkey account";
    }
    btn.href = "/portkey/signin";
  }

  function updateReviewRunBuildMode(verified, status) {
    const tagline = document.getElementById("header-tagline");
    const steps = document.getElementById("reviewrun-steps");
    const banner = document.getElementById("portkey-build-banner");
    if (tagline) {
      tagline.textContent = verified
        ? "Governance + build — packet authority with your Portkey gateway"
        : "Packet authority for AI access and spend review";
    }
    if (steps) {
      steps.innerHTML = verified
        ? `<li><strong>Attach repo:</strong> use the demo GitHub access request.</li>
           <li><strong>Run IA:</strong> generate the packet-backed review.</li>
           <li><strong>Build via Portkey:</strong> route inference through <code>${status?.resolved_model || resolvedModel(status?.provider_slug, status?.model_suffix)}</code>.</li>
           <li><strong>Act:</strong> follow the one named human action.</li>`
        : `<li><strong>Attach repo:</strong> use the demo GitHub access request.</li>
           <li><strong>Run IA:</strong> generate the packet-backed review.</li>
           <li><strong>Act:</strong> follow the one named human action.</li>`;
    }
    if (banner) {
      banner.hidden = !verified;
      if (verified) {
        banner.textContent = `Portkey connected — ReviewRun is in governance + build mode (${status?.resolved_model || "gateway ready"}).`;
      }
    }
  }

  function updatePortkeyStackPill(verified, status) {
    const stack = document.getElementById("stack-pills");
    if (!stack) return;
    let pill = stack.querySelector('[data-pill="portkey"]');
    if (!pill) {
      pill = document.createElement("span");
      pill.dataset.pill = "portkey";
      stack.prepend(pill);
    }
    if (verified) {
      pill.className = "pill on";
      pill.textContent = `Portkey: connected · ${status?.provider_slug || "gateway"}`;
    } else if (status?.has_saved_key || status?.connected) {
      pill.className = "pill";
      pill.textContent = "Portkey: setup pending";
    } else {
      pill.remove();
    }
  }

  function showPortkeyWelcomeToast() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("portkey") !== "connected") return;
    const toast = document.getElementById("portkey-welcome-toast");
    if (toast) {
      toast.hidden = false;
      setTimeout(() => {
        toast.hidden = true;
      }, 6000);
    }
    params.delete("portkey");
    const next = `${window.location.pathname}${params.toString() ? `?${params}` : ""}`;
    window.history.replaceState({}, "", next);
  }

  global.PortkeyConnect = {
    PROVIDER_KEY,
    MODEL_KEY,
    STATUS_KEY,
    normalizeProvider,
    resolvedModel,
    readStatusCache,
    writeStatusCache,
    clearStatusCache,
    syncPortkeyUi,
    showPortkeyWelcomeToast,
  };
})(window);
