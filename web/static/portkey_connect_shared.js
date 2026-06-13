/** Shared Portkey Plane B local cache + main-page sync helpers. */
(function initPortkeyConnectShared(global) {
  const PROVIDER_KEY = "ia_portkey_provider_slug";
  const MODEL_KEY = "ia_portkey_model_suffix";
  const STATUS_KEY = "ia_portkey_status_cache";

  function normalizeProvider(value) {
    return String(value || "").trim().replace(/^@+/, "");
  }

  function normalizeModelInput(provider, modelSuffix) {
    let providerSlug = normalizeProvider(provider);
    let model = String(modelSuffix || "").trim();
    if (model.startsWith("@")) {
      const route = model.replace(/^@+/, "");
      const slash = route.indexOf("/");
      if (slash > 0) {
        const routeSlug = route.slice(0, slash).trim();
        const routeModel = route.slice(slash + 1).trim();
        if (!providerSlug) providerSlug = routeSlug;
        model = routeModel;
      } else {
        model = route;
      }
    }
    return { providerSlug, modelSuffix: model };
  }

  function resolvedModel(provider, modelSuffix) {
    const { providerSlug, modelSuffix: model } = normalizeModelInput(provider, modelSuffix);
    const slug = providerSlug || "your-provider";
    const name = model || "gpt-4o-mini";
    return `@${slug}/${name}`;
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
    const meta = document.getElementById("portkey-connect-meta");
    if (!btn) return;
    if (verified) {
      btn.textContent = "Portkey connected";
      btn.classList.add("portkey-connected");
      btn.classList.remove("portkey-pending");
      btn.title = `Gateway: ${status?.resolved_model || resolvedModel(status?.provider_slug, status?.model_suffix)}`;
      if (meta) {
        meta.hidden = false;
        meta.textContent = `Governance + build · ${status?.resolved_model || resolvedModel(status?.provider_slug, status?.model_suffix)}`;
      }
    } else if (status?.has_saved_key || status?.connected) {
      btn.textContent = "Finish Portkey setup";
      btn.classList.remove("portkey-connected");
      btn.classList.add("portkey-pending");
      btn.title = "Key saved — finish provider setup";
      if (meta) {
        meta.hidden = true;
        meta.textContent = "";
      }
    } else {
      btn.textContent = "Connect PortKey";
      btn.classList.remove("portkey-connected", "portkey-pending");
      btn.title = "Connect your Portkey account";
      if (meta) {
        meta.hidden = true;
        meta.textContent = "";
      }
    }
    btn.href = "/portkey/signin";
  }

  function updateReviewRunBuildMode(verified, status) {
    const tagline = document.getElementById("header-tagline");
    const steps = document.getElementById("reviewrun-steps");
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
    updatePortkeyNavButton(verified, status);
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
    const meta = document.getElementById("portkey-connect-meta");
    if (meta) {
      meta.hidden = false;
      meta.textContent = "Connected — governance + build mode active";
      window.setTimeout(() => {
        const cache = readStatusCache();
        if (cache.verified) {
          meta.textContent = `Governance + build · ${cache.resolved_model || resolvedModel(cache.provider_slug, cache.model_suffix)}`;
        }
      }, 3200);
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
    normalizeModelInput,
    resolvedModel,
    readStatusCache,
    writeStatusCache,
    clearStatusCache,
    syncPortkeyUi,
    showPortkeyWelcomeToast,
  };
})(window);
