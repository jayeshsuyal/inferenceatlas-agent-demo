const STORAGE_KEY = "ia_session_id";

const messagesEl = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const btnSend = document.getElementById("btn-send");
const btnReset = document.getElementById("btn-reset");
const examplesList = document.getElementById("examples-list");
const stackPills = document.getElementById("stack-pills");
const catalogInfo = document.getElementById("catalog-info");

let sessionId = localStorage.getItem(STORAGE_KEY) || null;
let busy = false;

function setBusy(loading) {
  busy = loading;
  btnSend.disabled = loading;
  input.disabled = loading;
  btnSend.querySelector(".send-label").hidden = loading;
  btnSend.querySelector(".spinner").hidden = !loading;
}

function appendMessage(role, text, extraClass = "") {
  const wrap = document.createElement("div");
  wrap.className = `message ${role} ${extraClass}`.trim();

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (role === "assistant") {
    text.split("\n\n").forEach((para) => {
      if (!para.trim()) return;
      const p = document.createElement("p");
      p.textContent = para.trim();
      bubble.appendChild(p);
    });
    if (!bubble.childNodes.length) {
      const p = document.createElement("p");
      p.textContent = text;
      bubble.appendChild(p);
    }
  } else {
    bubble.textContent = text;
  }

  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return wrap;
}

function removeMessage(el) {
  if (el && el.parentNode) el.parentNode.removeChild(el);
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message || busy) return;

  appendMessage("user", message);
  input.value = "";
  setBusy(true);

  const loadingEl = appendMessage("assistant", "Thinking…", "loading");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(data.detail || `Request failed (${res.status})`);
    }

    sessionId = data.session_id;
    localStorage.setItem(STORAGE_KEY, sessionId);
    removeMessage(loadingEl);
    appendMessage("assistant", data.reply);
  } catch (err) {
    removeMessage(loadingEl);
    const errWrap = appendMessage("assistant", String(err.message || err), "error");
    errWrap.querySelector(".bubble").classList.add("error");
  } finally {
    setBusy(false);
    input.focus();
  }
}

async function resetChat() {
  if (sessionId) {
    try {
      await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
    } catch (_) {
      /* ignore */
    }
  }
  sessionId = null;
  localStorage.removeItem(STORAGE_KEY);
  messagesEl.innerHTML = "";
  appendMessage(
    "assistant",
    "New conversation started. Ask about pricing, catalog comparisons, or provider costs.",
    "welcome"
  );
}

async function loadMeta() {
  try {
    const [health, examples] = await Promise.all([
      fetch("/api/health").then((r) => r.json()),
      fetch("/api/examples").then((r) => r.json()),
    ]);

    stackPills.innerHTML = "";
    const pills = [
      ["LLM", `${health.llm_provider} · ${health.llm_model}`, health.ok],
      ["Tavily", health.tavily ? "on" : "off", health.tavily],
      ["Composio", health.composio ? (health.composio_dry_run ? "dry-run" : "on") : "off", health.composio],
    ];
    for (const [name, status, on] of pills) {
      const span = document.createElement("span");
      span.className = `pill ${on ? "on" : "off"}`;
      span.textContent = `${name}: ${status}`;
      stackPills.appendChild(span);
    }

    if (health.catalog) {
      catalogInfo.textContent = health.catalog;
    }

    examplesList.innerHTML = "";
    for (const ex of examples) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = ex.label;
      btn.title = ex.message;
      btn.addEventListener("click", () => {
        input.value = ex.message;
        sendMessage(ex.message);
      });
      li.appendChild(btn);
      examplesList.appendChild(li);
    }

    if (!health.ok) {
      appendMessage(
        "assistant",
        "Server has no LLM API key. Add NEBIUS_API_KEY or OPENAI_API_KEY to .env and restart the web server.",
        "error"
      );
    }
  } catch (err) {
    catalogInfo.textContent = "Could not reach API.";
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(input.value);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

btnReset.addEventListener("click", resetChat);

loadMeta();
