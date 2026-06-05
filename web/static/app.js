const STORAGE_KEY = "ia_session_id";
const REVIEW_SCOPE_KEY = "ia_review_scope";

const messagesEl = document.getElementById("messages");
const chatView = document.getElementById("chat-view");
const reviewView = document.getElementById("review-view");
const walkthroughView = document.getElementById("walkthrough-view");
const cycleFeed = document.getElementById("cycle-feed");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const btnSend = document.getElementById("btn-send");
const btnReset = document.getElementById("btn-reset");
const examplesList = document.getElementById("examples-list");
const stackPills = document.getElementById("stack-pills");
const catalogInfo = document.getElementById("catalog-info");
const mindPanel = document.getElementById("mind-panel");
const mindToast = document.getElementById("mind-toast");
const btnMindInit = document.getElementById("btn-mind-init");
const btnMindStep = document.getElementById("btn-mind-step");
const btnRunRehearsal = document.getElementById("btn-run-rehearsal");
const btnRunUploadedRehearsal = document.getElementById("btn-run-uploaded-rehearsal");
const btnLoadWalkthrough = document.getElementById("btn-load-walkthrough");
const btnCopyWalkthroughBrief = document.getElementById("btn-copy-walkthrough-brief");
const judgeStepsEl = document.getElementById("judge-steps");
const walkthroughStepsNav = document.getElementById("walkthrough-steps-nav");
const guideTitle = document.getElementById("guide-title");
const guideSubtitle = document.getElementById("guide-subtitle");
const blockedNote = document.getElementById("blocked-note");
const walkthroughToast = document.getElementById("walkthrough-toast");
const walkthroughTitle = document.getElementById("walkthrough-title");
const walkthroughSubtitle = document.getElementById("walkthrough-subtitle");
const walkthroughStrip = document.getElementById("walkthrough-strip");
const walkthroughActiveCard = document.getElementById("walkthrough-active-card");
const walkthroughDecisionCard = document.getElementById("walkthrough-decision-card");
const walkthroughSponsorCard = document.getElementById("walkthrough-sponsor-card");
const walkthroughReviewerCard = document.getElementById("walkthrough-reviewer-card");
const walkthroughExportCard = document.getElementById("walkthrough-export-card");
const reviewNote = document.getElementById("review-note");
const reviewFile = document.getElementById("review-file");
const reviewFileChip = document.getElementById("review-file-chip");
const customEvidenceFile = document.getElementById("custom-evidence-file");
const customEvidenceChip = document.getElementById("custom-evidence-chip");
const btnQueueEvidence = document.getElementById("btn-queue-evidence");
const chatFile = document.getElementById("chat-file");
const chatFileChip = document.getElementById("chat-file-chip");
const btnSkillsPlus = document.getElementById("btn-skills-plus");
const skillsFlyout = document.getElementById("skills-flyout");
const slashMenu = document.getElementById("slash-menu");
const skillsAnchor = document.getElementById("skills-anchor");
const skillChipsEl = document.getElementById("skill-chips");
const skillHintsEl = document.getElementById("skill-hints");

const SKILL_HINT_BY_ID = {
  decision_packet_generation: "What blocks production access for support triage?",
  proof_debt_extraction: "List proof debt owners and what each unblocks.",
  reviewer_routing: "Who must approve next and what action do they own?",
  policy_gate_evaluation: "Which scenarios are BLOCKED vs allowed for validation?",
  risk_aware_scenario_differentiation: "How do the three scenarios differ?",
  packet_diff_generation: "Compare proof gaps and production access across scenarios.",
  design_partner_trial_runner: "What did the trial normalize and recommend?",
  full_judge_harness: "Summarize the full judge proof path.",
};

const EMPTY_PROOF_TILES = [
  ["Packet lock", "Production false · writes false"],
  ["Sponsor proof", "Tavily evidence · Composio dry-run"],
  ["Cost guardrail", "Procurement shortlist · no savings guarantee"],
  ["Review lane", "Scoped validation · humans approve"],
];

let sessionId = localStorage.getItem(STORAGE_KEY) || crypto.randomUUID();
localStorage.setItem(STORAGE_KEY, sessionId);

let chatStorageScope = `chat_${sessionId}`;
let reviewStorageScope =
  localStorage.getItem(REVIEW_SCOPE_KEY) || `review_${sessionId}`;
localStorage.setItem(REVIEW_SCOPE_KEY, reviewStorageScope);

let busy = false;
let chatAttachmentIds = [];
let reviewAttachmentIds = [];
let customEvidenceAttachmentIds = [];
let judgeStep = 1;
let mindsInitialized = false;
let uiSkills = [];
let uiSkillCategories = [];
let slashActiveIndex = 0;
let slashFilter = "";
let skillsLoadError = null;
let skillsLoaded = false;
let walkthroughPayload = null;
let walkthroughActiveIndex = 0;
/** @type {Array<{id:string, name:string, slash:string, slash_trigger:string, what_it_proves:string}>} */
let selectedSkills = [];

function setBusy(loading) {
  busy = loading;
  btnSend.disabled = loading;
  input.disabled = loading;
  btnSend.querySelector(".send-label").hidden = loading;
  btnSend.querySelector(".spinner").hidden = !loading;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function downloadFile(fileId, label) {
  if (!fileId) {
    throw new Error("No file id");
  }
  const res = await fetch(`/api/files/${fileId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Download failed (${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = label.replace(/[^\w.\-]+/g, "_") || "download.txt";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function addDownloadButtons(container, files) {
  if (!files?.length) return;
  const links = document.createElement("div");
  links.className = "output-links";
  for (const f of files) {
    if (!f.file_id) continue;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dl-btn";
    btn.textContent = `↓ ${f.label || "Download"}`;
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await downloadFile(f.file_id, f.label);
      } catch (err) {
        btn.textContent = err.message || "Download failed";
        btn.classList.add("error");
      } finally {
        btn.disabled = false;
      }
    });
    links.appendChild(btn);
  }
  container.appendChild(links);
}

function appendMessage(role, text, extraClass = "", outputFiles = []) {
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
    addDownloadButtons(bubble, outputFiles.filter((f) => f.file_id));
  } else {
    bubble.textContent = text;
  }

  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return wrap;
}

function clearEmptyProofBoard() {
  document.getElementById("empty-proof-board")?.remove();
}

function renderEmptyProofBoard() {
  clearEmptyProofBoard();
  const board = document.createElement("div");
  board.className = "empty-proof-board";
  board.id = "empty-proof-board";
  board.setAttribute("aria-label", "Current public proof state");
  for (const [label, value] of EMPTY_PROOF_TILES) {
    const tile = document.createElement("article");
    tile.className = "proof-tile";
    tile.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>`;
    board.appendChild(tile);
  }
  messagesEl.appendChild(board);
}

function removeMessage(el) {
  if (el && el.parentNode) el.parentNode.removeChild(el);
}

function showMindToast(text, isError = false) {
  mindToast.textContent = text || "";
  mindToast.classList.toggle("error", isError);
}

function setJudgeStep(n) {
  judgeStep = n;
  judgeStepsEl.querySelectorAll("li").forEach((li, i) => {
    li.classList.toggle("active", i + 1 === n);
  });
}

function showReviewPanel() {
  document.querySelector('.tab[data-tab="review"]')?.click();
}

function showWalkthroughPanel() {
  document.querySelector('.tab[data-tab="walkthrough"]')?.click();
}

async function uploadFile(channel, fileInput, chipEl, idStore) {
  const file = fileInput.files?.[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("channel", channel);
  formData.append("session_id", sessionId);
  formData.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Upload failed");
  if (channel === "chat") {
    chatStorageScope = data.storage_scope;
  } else {
    reviewStorageScope = data.storage_scope;
    localStorage.setItem(REVIEW_SCOPE_KEY, reviewStorageScope);
  }
  idStore.length = 0;
  idStore.push(data.file_id);
  chipEl.hidden = false;
  chipEl.textContent = `Attached: ${data.name}`;
  chipEl.title = data.preview || "";
  fileInput.value = "";
  return data;
}

async function uploadCustomEvidenceFiles() {
  const files = Array.from(customEvidenceFile.files || []).slice(0, 8);
  if (!files.length) return;
  const names = [];
  customEvidenceAttachmentIds = [];
  for (const file of files) {
    const formData = new FormData();
    formData.append("channel", "review");
    formData.append("session_id", sessionId);
    formData.append("file", file);
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Upload failed");
    reviewStorageScope = data.storage_scope;
    localStorage.setItem(REVIEW_SCOPE_KEY, reviewStorageScope);
    customEvidenceAttachmentIds.push(data.file_id);
    names.push(data.name);
  }
  customEvidenceChip.hidden = false;
  customEvidenceChip.classList.remove("error");
  customEvidenceChip.textContent = `Uploaded: ${names.join(", ")}`;
  customEvidenceChip.title = names.join("\n");
  customEvidenceFile.value = "";
}

chatFile.addEventListener("change", async () => {
  try {
    await uploadFile("chat", chatFile, chatFileChip, chatAttachmentIds);
  } catch (err) {
    chatFileChip.hidden = false;
    chatFileChip.textContent = err.message || "Upload failed";
    chatFileChip.classList.add("error");
  }
});

reviewFile.addEventListener("change", async () => {
  try {
    await uploadFile("review", reviewFile, reviewFileChip, reviewAttachmentIds);
    setJudgeStep(2);
  } catch (err) {
    showMindToast(err.message || "Upload failed", true);
  }
});

customEvidenceFile.addEventListener("change", async () => {
  try {
    await uploadCustomEvidenceFiles();
    setJudgeStep(2);
  } catch (err) {
    customEvidenceChip.hidden = false;
    customEvidenceChip.classList.add("error");
    customEvidenceChip.textContent = err.message || "Upload failed";
  }
});

function appendUserMessage(message, skills = []) {
  clearEmptyProofBoard();
  const wrap = document.createElement("div");
  wrap.className = "message user";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (skills.length) {
    const row = document.createElement("div");
    row.className = "user-skill-chips";
    skills.forEach((skill) => {
      const a = document.createElement("a");
      a.href = "#";
      a.className = "skill-chip-link";
      a.textContent = skill.slash_trigger || `/${skill.slash}`;
      a.title = `${skill.name}\n${skill.what_it_proves || ""}`;
      a.addEventListener("click", (e) => e.preventDefault());
      row.appendChild(a);
    });
    bubble.appendChild(row);
  }

  const text = (message || "").trim();
  if (text) {
    const p = document.createElement("p");
    p.textContent = text;
    bubble.appendChild(p);
  } else if (skills.length) {
    const p = document.createElement("p");
    p.className = "user-skill-only";
    p.textContent = "Answer using the attached skills.";
    bubble.appendChild(p);
  }

  if (chatAttachmentIds.length) {
    const att = document.createElement("p");
    att.className = "user-attach-hint";
    att.textContent = "[+ file attached]";
    bubble.appendChild(att);
  }

  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return wrap;
}

function renderSkillHints() {
  if (!skillHintsEl) return;
  if (!selectedSkills.length) {
    skillHintsEl.hidden = true;
    skillHintsEl.textContent = "";
    return;
  }
  const hints = selectedSkills
    .map((s) => SKILL_HINT_BY_ID[s.id])
    .filter(Boolean)
    .slice(0, 2);
  if (!hints.length) {
    hints.push("Summarize what these skills prove and what humans must approve.");
  }
  skillHintsEl.hidden = false;
  skillHintsEl.textContent = `Try: ${hints.join(" · ")}`;
}

function renderSkillChips() {
  if (!skillChipsEl) return;
  skillChipsEl.innerHTML = "";
  if (!selectedSkills.length) {
    skillChipsEl.hidden = true;
    renderSkillHints();
    return;
  }
  skillChipsEl.hidden = false;
  selectedSkills.forEach((skill) => {
    const chip = document.createElement("span");
    chip.className = "skill-chip";
    const link = document.createElement("a");
    link.href = "#";
    link.className = "skill-chip-link";
    link.textContent = skill.slash_trigger || `/${skill.slash}`;
    link.title = `${skill.name}\n${skill.what_it_proves || ""}`;
    link.addEventListener("click", (e) => e.preventDefault());
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "skill-chip-remove";
    rm.setAttribute("aria-label", `Remove ${skill.name}`);
    rm.textContent = "×";
    rm.addEventListener("click", () => detachSkill(skill.id));
    chip.appendChild(link);
    chip.appendChild(rm);
    skillChipsEl.appendChild(chip);
  });
  renderSkillHints();
}

function stripTrailingSlashToken() {
  const pos = input.selectionStart ?? input.value.length;
  const before = input.value.slice(0, pos).replace(/\/[a-zA-Z0-9-]*$/, "");
  const after = input.value.slice(pos);
  input.value = before + after;
}

function attachSkill(skill) {
  if (selectedSkills.some((s) => s.id === skill.id)) {
    stripTrailingSlashToken();
    closeSlashMenu();
    closeSkillsFlyout();
    input.focus();
    return;
  }
  selectedSkills.push(skill);
  renderSkillChips();
  stripTrailingSlashToken();
  closeSlashMenu();
  closeSkillsFlyout();
  input.focus();
}

function detachSkill(skillId) {
  selectedSkills = selectedSkills.filter((s) => s.id !== skillId);
  renderSkillChips();
}

function clearSelectedSkills() {
  selectedSkills = [];
  renderSkillChips();
}

async function sendMessage(text) {
  const message = text.trim();
  const skill_ids = selectedSkills.map((s) => s.id);
  if ((!message && !skill_ids.length) || busy) return;

  const skillsSnapshot = selectedSkills.slice();
  appendUserMessage(message, skillsSnapshot);
  input.value = "";
  clearSelectedSkills();
  setBusy(true);

  const loadingEl = appendMessage("assistant", "Thinking…", "loading");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        attachment_ids: chatAttachmentIds,
        skill_ids,
        skill_context_position: "prepend",
      }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(data.detail || `Request failed (${res.status})`);
    }

    sessionId = data.session_id;
    localStorage.setItem(STORAGE_KEY, sessionId);
    chatStorageScope = `chat_${sessionId}`;
    removeMessage(loadingEl);
    appendMessage("assistant", data.reply, "", data.output_files || []);
    chatAttachmentIds = [];
    chatFileChip.hidden = true;
    chatFileChip.classList.remove("error");
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
  sessionId = crypto.randomUUID();
  localStorage.setItem(STORAGE_KEY, sessionId);
  chatStorageScope = `chat_${sessionId}`;
  chatAttachmentIds = [];
  chatFileChip.hidden = true;
  clearSelectedSkills();
  closeSlashMenu();
  messagesEl.innerHTML = "";
  appendMessage(
    "assistant",
    "Welcome. Compare AI inference costs, explore the catalog, or ask whether an agent should get tool access.\n\nAttach /packet, /gate, etc., ask a review question, then Send. Skills inject real DecisionPacket facts (no catalog tool loop).",
    "welcome"
  );
  renderEmptyProofBoard();
}

function renderMindCard(m, pulse = false) {
  const card = document.createElement("article");
  card.className = `mind-card-v2${pulse ? " pulse" : ""}`;

  const head = document.createElement("div");
  head.className = "card-head";
  const title = document.createElement("h4");
  title.textContent = m.title || m.scenario;
  const badge = document.createElement("span");
  badge.className = `badge ${m.access_class || "review"}`;
  badge.title = m.blocked_explainer || "";
  badge.textContent = m.access_badge || "BLOCKED";
  head.appendChild(title);
  head.appendChild(badge);
  card.appendChild(head);

  const verdict = document.createElement("p");
  verdict.className = "card-verdict";
  verdict.innerHTML = `<strong>Next step:</strong> ${escapeHtml(
    m.recommended_step || "See live results panel →"
  )}`;
  card.appendChild(verdict);

  const stats = document.createElement("div");
  stats.className = "mind-stats";
  const statItems = [
    [String(m.tick ?? 0), "Cycle"],
    [String(m.open_proof_items ?? 0), "Proof gaps"],
    [String(m.proof_health_score ?? "—"), "Proof health"],
  ];
  for (const [val, label] of statItems) {
    const s = document.createElement("div");
    s.className = "stat";
    s.innerHTML = `<span class="stat-val">${escapeHtml(String(val))}</span><span class="stat-label">${escapeHtml(label)}</span>`;
    stats.appendChild(s);
  }
  card.appendChild(stats);

  return card;
}

function renderArtifactLinks(artifacts, container) {
  addDownloadButtons(container, artifacts || []);
}

function renderCycleFeed(cycleResults, emptyMessage) {
  cycleFeed.innerHTML = "";
  if (!cycleResults?.length) {
    const p = document.createElement("p");
    p.className = "empty-feed";
    p.textContent =
      emptyMessage ||
      "No cycle data yet. Click “1. Reset scenarios”, then “3. Run review cycle”.";
    cycleFeed.appendChild(p);
    return;
  }

  for (const cr of cycleResults) {
    const card = document.createElement("article");
    card.className = "cycle-card highlight";
    const h = document.createElement("h3");
    h.textContent = `${cr.title} — cycle #${cr.live?.tick ?? "?"}`;
    card.appendChild(h);

    const delta = document.createElement("ul");
    delta.className = "delta-list";
    (cr.delta || []).forEach((line) => {
      const li = document.createElement("li");
      li.textContent = line;
      delta.appendChild(li);
    });
    card.appendChild(delta);

    if (cr.narrative?.length) {
      const nar = document.createElement("ul");
      nar.className = "narrative-list";
      cr.narrative.forEach((line) => {
        const li = document.createElement("li");
        li.textContent = line;
        nar.appendChild(li);
      });
      card.appendChild(nar);
    }

    const live = document.createElement("div");
    live.className = "live-block";
    live.innerHTML = [
      `<strong>Verdict:</strong> ${escapeHtml(cr.live?.verdict_short || "")}`,
      `<br/><strong>Recommended:</strong> ${escapeHtml(cr.live?.recommended_step || "")}`,
      `<br/><strong>Scoped validation:</strong> ${
        cr.live?.scoped_validation ? "Allowed (dry-run)" : "Blocked"
      }`,
      `<br/><strong>Evidence notes:</strong> ${cr.live?.evidence_count ?? 0}`,
      `<br/><strong>Proof gaps:</strong> ${cr.live?.open_proof_items ?? 0}`,
    ].join("");
    card.appendChild(live);

    renderArtifactLinks(cr.live?.artifacts, card);
    cycleFeed.appendChild(card);
  }
}

function boolLabel(value) {
  return value ? "True" : "False";
}

function renderRehearsalCard(data) {
  cycleFeed.innerHTML = "";
  const card = document.createElement("article");
  card.className = "cycle-card sponsor-rehearsal highlight";

  const h = document.createElement("h3");
  h.textContent = data.title || "Sponsor evidence rehearsal";
  card.appendChild(h);

  const lock = document.createElement("div");
  lock.className = "rehearsal-locks";
  const lockItems = [
    ["Decision", data.decision_lock?.decision_code || ""],
    ["Production", boolLabel(data.decision_lock?.production_access)],
    ["Grants", boolLabel(data.decision_lock?.permission_grants)],
    ["Writes", boolLabel(data.decision_lock?.external_writes)],
    ["Sponsor changes decision", boolLabel(data.decision_lock?.can_sponsor_change_decision)],
  ];
  lockItems.forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "lock-item";
    item.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>`;
    lock.appendChild(item);
  });
  card.appendChild(lock);

  const summary = document.createElement("div");
  summary.className = "live-block";
  summary.innerHTML = [
    `<strong>Evidence dir:</strong> ${escapeHtml(data.live_evidence_rehearsal?.evidence_dir || "")}`,
    `<br/><strong>Sanitized providers:</strong> ${escapeHtml(String(data.live_evidence_rehearsal?.sanitized_provider_count ?? 0))}`,
    `<br/><strong>Decision locked:</strong> ${boolLabel(data.live_evidence_rehearsal?.decision_locked)}`,
    `<br/><strong>Human review required:</strong> ${boolLabel(data.safety_boundary?.requires_human_review)}`,
  ].join("");
  card.appendChild(summary);

  if (data.accepted_files?.length) {
    const accepted = document.createElement("p");
    accepted.className = "accepted-files";
    accepted.textContent = `Accepted: ${data.accepted_files
      .map((item) => `${item.provider}:${item.filename}`)
      .join(" · ")}`;
    card.appendChild(accepted);
  }

  const tableWrap = document.createElement("div");
  tableWrap.className = "provider-table-wrap";
  const rows = (data.providers || [])
    .map(
      (p) => `
        <tr>
          <td>${escapeHtml(p.provider)}</td>
          <td>${escapeHtml(p.proof_pack_type)}</td>
          <td>${escapeHtml(String(p.rehearsal_item_count || 0))}</td>
          <td>${boolLabel(p.evidence_attached)}</td>
          <td>${boolLabel(p.can_approve_access)}</td>
          <td>${boolLabel(p.would_execute)}</td>
        </tr>`
    )
    .join("");
  tableWrap.innerHTML = `
    <table class="provider-table">
      <thead>
        <tr>
          <th>Provider</th>
          <th>Proof pack</th>
          <th>Items</th>
          <th>Attached</th>
          <th>Can approve</th>
          <th>Executes</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
  card.appendChild(tableWrap);

  renderArtifactLinks(data.output_files || [], card);
  cycleFeed.appendChild(card);
}

function setWalkthroughToast(text, isError = false) {
  if (!walkthroughToast) return;
  walkthroughToast.textContent = text || "";
  walkthroughToast.classList.toggle("error", isError);
}

function renderMiniList(items, { limit = 4 } = {}) {
  const ul = document.createElement("ul");
  ul.className = "mini-list";
  (items || []).slice(0, limit).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = typeof item === "string" ? item : JSON.stringify(item);
    ul.appendChild(li);
  });
  if ((items || []).length > limit) {
    const li = document.createElement("li");
    li.textContent = `${items.length - limit} more in export`;
    ul.appendChild(li);
  }
  return ul;
}

function renderWalkthroughNav(data) {
  walkthroughStepsNav.innerHTML = "";
  (data.steps || []).forEach((step, index) => {
    const li = document.createElement("li");
    li.classList.toggle("active", index === walkthroughActiveIndex);
    li.innerHTML = `<strong>${escapeHtml(step.label)}</strong> ${escapeHtml(step.title)}`;
    li.addEventListener("click", () => {
      walkthroughActiveIndex = index;
      renderWalkthrough(data);
    });
    walkthroughStepsNav.appendChild(li);
  });
}

function renderWalkthroughStrip(data) {
  walkthroughStrip.innerHTML = "";
  (data.steps || []).forEach((step, index) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `walk-step${index === walkthroughActiveIndex ? " active" : ""}`;
    btn.innerHTML = `<span>${escapeHtml(String(index + 1))}</span><strong>${escapeHtml(step.label)}</strong>`;
    btn.addEventListener("click", () => {
      walkthroughActiveIndex = index;
      renderWalkthrough(data);
    });
    walkthroughStrip.appendChild(btn);
  });
}

function renderActiveWalkthroughCard(data) {
  const step = data.steps?.[walkthroughActiveIndex] || data.steps?.[0];
  walkthroughActiveCard.innerHTML = "";
  if (!step) return;
  const label = document.createElement("span");
  label.className = "eyebrow";
  label.textContent = step.label;
  const h = document.createElement("h3");
  h.textContent = step.title;
  const summary = document.createElement("p");
  summary.className = "walkthrough-summary";
  summary.textContent = step.summary;
  const fact = document.createElement("code");
  fact.className = "walkthrough-fact";
  fact.textContent = step.primary_fact;
  const boundary = document.createElement("p");
  boundary.className = "safety-anchor";
  boundary.textContent = step.boundary;
  walkthroughActiveCard.append(label, h, summary, fact, boundary);
}

function renderDecisionCard(data) {
  const decision = data.decision || {};
  walkthroughDecisionCard.innerHTML = `
    <span class="eyebrow">Decision lock</span>
    <h3>${escapeHtml(decision.verdict_class || "review_required")}</h3>
    <div class="walk-metrics">
      <div><span>Production</span><strong>${escapeHtml(String(decision.production_access))}</strong></div>
      <div><span>Grants</span><strong>${escapeHtml(String(decision.permission_grants))}</strong></div>
      <div><span>Writes</span><strong>${escapeHtml(String(decision.external_writes))}</strong></div>
      <div><span>Sponsors change</span><strong>${escapeHtml(String(decision.sponsors_can_change_decision))}</strong></div>
    </div>
    <p class="walkthrough-summary">${escapeHtml(decision.next_human_action || "")}</p>
  `;
}

function renderSponsorCard(data) {
  walkthroughSponsorCard.innerHTML = `
    <span class="eyebrow">Sponsor proof roles</span>
    <h3>Proof contributors</h3>
  `;
  const list = document.createElement("div");
  list.className = "sponsor-role-list";
  (data.sponsor_roles || []).forEach((item) => {
    const row = document.createElement("article");
    row.className = "sponsor-role-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(item.provider)}</strong>
        <span>${escapeHtml(item.verb)} ${escapeHtml(item.role)}</span>
      </div>
      <code>${escapeHtml(item.proof_type)}</code>
      <small>changes decision: ${escapeHtml(String(item.can_change_decision))}</small>
    `;
    list.appendChild(row);
  });
  walkthroughSponsorCard.appendChild(list);
}

function renderReviewerCard(data) {
  walkthroughReviewerCard.innerHTML = `
    <span class="eyebrow">Reviewer routing</span>
    <h3>${escapeHtml(String(data.reviewer_routing?.length || 0))} owner gates</h3>
  `;
  const routes = (data.reviewer_routing || []).map(
    (item) => `${item.owner}: ${item.decision_needed}`
  );
  walkthroughReviewerCard.appendChild(renderMiniList(routes, { limit: 4 }));
}

function renderExportCard(data) {
  walkthroughExportCard.innerHTML = `
    <span class="eyebrow">Export</span>
    <h3>PilotMemo</h3>
    <p class="walkthrough-summary">${escapeHtml(data.safety_anchor || "")}</p>
  `;
  const actions = document.createElement("div");
  actions.className = "walk-actions";
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "btn-primary";
  copy.textContent = "Copy review brief";
  copy.addEventListener("click", () => copyWalkthroughBrief());
  const review = document.createElement("button");
  review.type = "button";
  review.className = "btn-ghost";
  review.textContent = "Run review cycle";
  review.addEventListener("click", () => {
    showReviewPanel();
    mindStep();
  });
  actions.append(copy, review);
  walkthroughExportCard.appendChild(actions);
  renderArtifactLinks(data.output_files || [], walkthroughExportCard);
}

function renderWalkthrough(data) {
  walkthroughPayload = data;
  walkthroughTitle.textContent = data.title || "Design partner walkthrough";
  walkthroughSubtitle.textContent = data.subtitle || "";
  btnCopyWalkthroughBrief.disabled = !data.copy_review_brief;
  renderWalkthroughNav(data);
  renderWalkthroughStrip(data);
  renderActiveWalkthroughCard(data);
  renderDecisionCard(data);
  renderSponsorCard(data);
  renderReviewerCard(data);
  renderExportCard(data);
}

async function loadWalkthrough({ silent = false } = {}) {
  btnLoadWalkthrough.disabled = true;
  if (!silent) setWalkthroughToast("Loading walkthrough...");
  try {
    const res = await fetch("/api/walkthrough");
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Walkthrough failed");
    renderWalkthrough(data);
    setWalkthroughToast("Walkthrough loaded. PilotMemo export is ready.");
  } catch (err) {
    setWalkthroughToast(String(err.message || err), true);
    walkthroughActiveCard.innerHTML = `<p class="empty-feed">Walkthrough failed: ${escapeHtml(err.message || err)}</p>`;
  } finally {
    btnLoadWalkthrough.disabled = false;
  }
}

async function copyWalkthroughBrief() {
  if (!walkthroughPayload?.copy_review_brief) {
    await loadWalkthrough({ silent: true });
  }
  const text = walkthroughPayload?.copy_review_brief || "";
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    setWalkthroughToast("Review brief copied.");
  } catch (_) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
    setWalkthroughToast("Review brief copied.");
  }
}

function setupTabs() {
  const tabs = document.querySelectorAll(".sidebar-tabs .tab");
  const panels = {
    start: document.getElementById("panel-start"),
    walkthrough: document.getElementById("panel-walkthrough"),
    review: document.getElementById("panel-review"),
  };

  tabs.forEach((tab) => {
    tab.addEventListener("click", async () => {
      const id = tab.dataset.tab;
      tabs.forEach((t) => t.classList.toggle("active", t === tab));
      Object.entries(panels).forEach(([key, panel]) => {
        if (!panel) return;
        const on = key === id;
        panel.hidden = !on;
        panel.classList.toggle("active", on);
      });
      const isReview = id === "review";
      const isWalkthrough = id === "walkthrough";
      chatView.hidden = isReview || isWalkthrough;
      reviewView.hidden = !isReview;
      walkthroughView.hidden = !isWalkthrough;
      if (isReview) {
        await loadGuide();
        await ensureMindsReady();
        await loadMind();
      } else if (isWalkthrough) {
        if (!walkthroughPayload) {
          await loadWalkthrough({ silent: true });
        }
      }
    });
  });
}

async function loadGuide() {
  try {
    const data = await fetch("/api/mind/guide").then((r) => r.json());
    guideTitle.textContent = data.title || "Access review";
    guideSubtitle.textContent = data.subtitle || "";
    blockedNote.textContent = data.expect_blocked
      ? "Expected: Production access stays BLOCKED in this public harness until a human approves outside the demo."
      : "";
    judgeStepsEl.innerHTML = "";
    (data.steps || []).forEach((step, i) => {
      const li = document.createElement("li");
      if (i + 1 === judgeStep) li.classList.add("active");
      li.innerHTML = `<strong>${escapeHtml(step.title)}</strong> ${escapeHtml(step.detail)}`;
      judgeStepsEl.appendChild(li);
    });
  } catch (_) {
    /* ignore */
  }
}

async function ensureMindsReady() {
  if (mindsInitialized) return;
  try {
    const res = await fetch("/api/mind");
    const data = await res.json();
    if (data.initialized && data.minds?.length) {
      mindsInitialized = true;
      return;
    }
  } catch (_) {
    /* fall through to init */
  }
  await mindInit(true);
}

async function loadMeta() {
  try {
    const [health, examples] = await Promise.all([
      fetch("/api/health").then((r) => r.json()),
      fetch("/api/examples").then((r) => r.json()),
    ]);

    stackPills.innerHTML = "";
    const pills = [
      ["LLM", `${health.llm_provider} · live`, health.ok],
      ["Tavily", health.tavily ? "on" : "off", health.tavily],
      ["Composio", health.composio ? (health.composio_dry_run ? "dry-run" : "on") : "off", health.composio],
    ];
    for (const [name, status, on] of pills) {
      const span = document.createElement("span");
      span.className = `pill ${on ? "on" : "off"}`;
      span.textContent = `${name}: ${status}`;
      stackPills.appendChild(span);
    }

    if (health.catalog) catalogInfo.textContent = health.catalog;

    examplesList.innerHTML = "";
    for (const ex of examples) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "example-btn";
      btn.innerHTML = `<span class="ex-title">${escapeHtml(ex.label)}</span><span class="ex-desc">${escapeHtml(ex.description || "")}</span>`;
      btn.addEventListener("click", () => {
        document.querySelector('.tab[data-tab="start"]')?.click();
        input.value = ex.message;
        sendMessage(ex.message);
      });
      li.appendChild(btn);
      examplesList.appendChild(li);
    }

    if (!health.deps_ok) {
      appendMessage(
        "assistant",
        `Missing Python packages. ${health.deps_hint || "pip install -r agent/requirements.txt"}`,
        "error"
      );
    } else if (!health.ok) {
      appendMessage(
        "assistant",
        "Server has no LLM API key. Add NEBIUS_API_KEY or OPENAI_API_KEY to .env and restart.",
        "error"
      );
    }
  } catch (_) {
    catalogInfo.textContent = "Could not reach API.";
  }
}

async function loadMind() {
  try {
    const res = await fetch("/api/mind");
    const data = await res.json();
    mindPanel.innerHTML = "";
    if (!data.minds?.length) {
      const empty = document.createElement("p");
      empty.className = "sidebar-hint";
      empty.textContent = 'Click "1. Reset scenarios" to load live packets.';
      mindPanel.appendChild(empty);
      return;
    }
    mindsInitialized = true;
    for (const m of data.minds) {
      mindPanel.appendChild(renderMindCard(m));
    }
  } catch (_) {
    mindPanel.innerHTML = "";
    const err = document.createElement("p");
    err.className = "sidebar-hint";
    err.textContent = "Access review API unavailable — is the server running?";
    mindPanel.appendChild(err);
  }
}

async function mindInit(silent = false) {
  btnMindInit.disabled = true;
  btnMindStep.disabled = true;
  if (!silent) showMindToast("Resetting live scenario packets…");
  try {
    const res = await fetch("/api/mind/init", { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Reset failed");
    mindsInitialized = true;
    showMindToast(data.message || "Reset complete.");
    setJudgeStep(3);
    showReviewPanel();
    renderCycleFeed(data.cycle_results, null);
    mindPanel.innerHTML = "";
    for (const m of data.minds || []) {
      mindPanel.appendChild(renderMindCard(m));
    }
  } catch (err) {
    showMindToast(String(err.message || err), true);
    renderCycleFeed(null, `Reset failed: ${err.message || err}`);
  } finally {
    btnMindInit.disabled = false;
    btnMindStep.disabled = false;
  }
}

async function mindStep() {
  btnMindInit.disabled = true;
  btnMindStep.disabled = true;
  showMindToast("Running live review cycle on all 3 scenarios…");
  try {
    if (!mindsInitialized) {
      await mindInit(true);
    }
    const res = await fetch("/api/mind/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Step failed");
    if (!data.cycle_results?.length) {
      throw new Error("Server returned no cycle results — restart the web server.");
    }
    showMindToast(data.message || "Review cycle complete.");
    setJudgeStep(4);
    showReviewPanel();
    renderCycleFeed(data.cycle_results);
    mindPanel.innerHTML = "";
    for (const m of data.minds || []) {
      mindPanel.appendChild(renderMindCard(m, true));
    }
  } catch (err) {
    showMindToast(String(err.message || err), true);
    renderCycleFeed(null, `Review cycle failed: ${err.message || err}`);
  } finally {
    btnMindInit.disabled = false;
    btnMindStep.disabled = false;
  }
}

async function queueEvidence() {
  const text = reviewNote.value.trim();
  if (!text && !reviewAttachmentIds.length) {
    showMindToast("Add a note or attach a file first.", true);
    return;
  }
  btnQueueEvidence.disabled = true;
  try {
    if (!mindsInitialized) await mindInit(true);
    const res = await fetch("/api/mind/observe/full", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario: "support_triage_agent",
        text,
        attachment_ids: reviewAttachmentIds,
        storage_scope: reviewStorageScope,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Queue failed");
    showMindToast(
      `${data.message || "Queued."} (${data.queued_observations} pending)`
    );
    reviewNote.value = "";
    reviewAttachmentIds = [];
    reviewFileChip.hidden = true;
    setJudgeStep(3);
  } catch (err) {
    showMindToast(String(err.message || err), true);
  } finally {
    btnQueueEvidence.disabled = false;
  }
}

async function runSponsorRehearsal() {
  btnRunRehearsal.disabled = true;
  showMindToast("Running sponsor evidence rehearsal...");
  try {
    const res = await fetch("/api/rehearsal/live-evidence", { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Rehearsal failed");
    showMindToast(data.message || "Sponsor rehearsal complete.");
    setJudgeStep(3);
    showReviewPanel();
    renderRehearsalCard(data);
  } catch (err) {
    showMindToast(String(err.message || err), true);
    renderCycleFeed(null, `Sponsor rehearsal failed: ${err.message || err}`);
  } finally {
    btnRunRehearsal.disabled = false;
  }
}

async function runUploadedRehearsal() {
  if (!customEvidenceAttachmentIds.length) {
    showMindToast("Upload provider JSON first.", true);
    return;
  }
  btnRunUploadedRehearsal.disabled = true;
  showMindToast("Validating uploaded sponsor evidence...");
  try {
    const res = await fetch("/api/rehearsal/custom-evidence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        attachment_ids: customEvidenceAttachmentIds,
        storage_scope: reviewStorageScope,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Uploaded rehearsal failed");
    showMindToast(data.message || "Uploaded rehearsal complete.");
    setJudgeStep(3);
    showReviewPanel();
    renderRehearsalCard(data);
  } catch (err) {
    showMindToast(String(err.message || err), true);
    renderCycleFeed(null, `Uploaded rehearsal rejected: ${err.message || err}`);
  } finally {
    btnRunUploadedRehearsal.disabled = false;
  }
}

function closeSkillsFlyout() {
  skillsFlyout.hidden = true;
  btnSkillsPlus.setAttribute("aria-expanded", "false");
}

function closeSlashMenu() {
  slashMenu.hidden = true;
  slashFilter = "";
}

function isSlashModeActive() {
  const value = input.value;
  const pos = input.selectionStart ?? value.length;
  return /\/[a-zA-Z0-9-]*$/.test(value.slice(0, pos));
}

function readSlashFilter() {
  const value = input.value;
  const pos = input.selectionStart ?? value.length;
  const before = value.slice(0, pos);
  const match = before.match(/\/([a-zA-Z0-9-]*)$/);
  return match ? match[1].toLowerCase() : null;
}

function filteredSkills() {
  const q = slashFilter.toLowerCase();
  const list = !q
    ? uiSkills.slice()
    : uiSkills.filter((s) => {
        const hay = `${s.slash} ${s.name} ${s.id} ${s.slash_trigger || ""}`.toLowerCase();
        return hay.includes(q);
      });
  return list.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
}

function renderSkillMenuItems(container, skills, { onPick, activeIndex = 0 }) {
  container.innerHTML = "";
  if (!skills.length) {
    const empty = document.createElement("p");
    empty.className = "slash-menu-header";
    empty.textContent = "No matching skills";
    container.appendChild(empty);
    return;
  }
  skills.forEach((skill, index) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `skill-menu-item${index === activeIndex ? " active" : ""}`;
    btn.role = "option";
    btn.innerHTML = `<span class="skill-name">${escapeHtml(skill.name)}</span><span class="skill-meta"><span class="skill-slash">/${escapeHtml(skill.slash)}</span> — ${escapeHtml(skill.what_it_proves.slice(0, 90))}${skill.what_it_proves.length > 90 ? "…" : ""}</span>`;
    btn.addEventListener("mousedown", (e) => {
      e.preventDefault();
      onPick(skill);
    });
    container.appendChild(btn);
  });
}

function renderSkillsFlyout() {
  skillsFlyout.innerHTML = "";
  if (skillsLoadError && !uiSkills.length) {
    const err = document.createElement("p");
    err.className = "slash-menu-empty";
    err.textContent = skillsLoadError;
    skillsFlyout.appendChild(err);
    return;
  }
  if (!uiSkills.length) {
    const wait = document.createElement("p");
    wait.className = "slash-menu-empty";
    wait.textContent = "Loading skills…";
    skillsFlyout.appendChild(wait);
    return;
  }
  const sorted = uiSkills
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
  for (const skill of sorted) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "skill-menu-item";
    btn.role = "menuitem";
    btn.innerHTML = `<span class="skill-name">${escapeHtml(skill.name)}</span><span class="skill-meta"><span class="skill-slash">/${escapeHtml(skill.slash)}</span></span>`;
    btn.addEventListener("click", () => {
      attachSkill(skill);
    });
    skillsFlyout.appendChild(btn);
  }
}

function updateSlashMenu() {
  if (!isSlashModeActive()) {
    closeSlashMenu();
    return;
  }

  slashMenu.hidden = false;
  const header = document.createElement("div");
  header.className = "slash-menu-header";
  const n = uiSkills.length;
  header.textContent =
    n > 0
      ? `${filteredSkills().length} of ${n} skills — ↑↓ move, Enter attach, Esc close`
      : "Loading skills…";
  slashMenu.innerHTML = "";
  slashMenu.appendChild(header);

  const list = document.createElement("div");
  list.className = "slash-menu-list";

  if (!uiSkills.length) {
    const loading = document.createElement("p");
    loading.className = "slash-menu-empty";
    loading.textContent = skillsLoadError || "Loading skill registry…";
    list.appendChild(loading);
    slashMenu.appendChild(list);
    return;
  }

  const skills = filteredSkills();
  slashActiveIndex = Math.min(slashActiveIndex, Math.max(0, skills.length - 1));

  if (!skills.length) {
    const empty = document.createElement("p");
    empty.className = "slash-menu-empty";
    empty.textContent = `No skills match “/${slashFilter}”`;
    list.appendChild(empty);
  } else {
    renderSkillMenuItems(list, skills, {
      activeIndex: slashActiveIndex,
      onPick: (skill) => {
        attachSkill(skill);
      },
    });
  }
  slashMenu.appendChild(list);

  const activeEl = list.querySelector(".skill-menu-item.active");
  if (activeEl) {
    activeEl.scrollIntoView({ block: "nearest" });
  }
}

function onInputSlashCheck() {
  const filter = readSlashFilter();
  if (filter === null) {
    closeSlashMenu();
    return;
  }
  if (filter !== slashFilter) {
    slashActiveIndex = 0;
  }
  slashFilter = filter;
  updateSlashMenu();
}

async function applySkillsPayload(data, source) {
  uiSkills = data.skills || [];
  uiSkillCategories = data.categories || [];
  skillsLoaded = true;
  if (source === "static") {
    skillsLoadError =
      "Using bundled skills (server is outdated — restart: python3 -m web).";
  } else {
    skillsLoadError = null;
  }
  renderSkillsFlyout();
  if (isSlashModeActive()) updateSlashMenu();
}

async function loadUiSkills() {
  skillsLoadError = null;
  skillsLoaded = false;
  try {
    const res = await fetch("/api/skills");
    if (res.ok) {
      await applySkillsPayload(await res.json(), "api");
      return;
    }
    const fb = await fetch("/static/skills-registry.json");
    if (fb.ok) {
      await applySkillsPayload(await fb.json(), "static");
      return;
    }
    throw new Error(
      `Skills API returned ${res.status} and bundled registry missing. Stop the server and run: python3 -m web`
    );
  } catch (err) {
    uiSkills = [];
    skillsLoaded = false;
    skillsLoadError = err.message || String(err);
    console.error("Failed to load skills", err);
    renderSkillsFlyout();
    if (isSlashModeActive()) updateSlashMenu();
  }
}

btnSkillsPlus.addEventListener("click", async (e) => {
  e.stopPropagation();
  closeSlashMenu();
  if (!skillsLoaded && !uiSkills.length) {
    await loadUiSkills();
  }
  const willOpen = skillsFlyout.hidden;
  if (willOpen) {
    skillsFlyout.hidden = false;
    btnSkillsPlus.setAttribute("aria-expanded", "true");
    renderSkillsFlyout();
  } else {
    closeSkillsFlyout();
  }
});

document.addEventListener("click", (e) => {
  if (!skillsAnchor.contains(e.target)) closeSkillsFlyout();
});

input.addEventListener("input", onInputSlashCheck);

input.addEventListener("keydown", (e) => {
  if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
    requestAnimationFrame(() => {
      const filter = readSlashFilter();
      if (filter !== null) {
        slashFilter = filter;
        slashActiveIndex = 0;
        updateSlashMenu();
      }
    });
  }

  if (!slashMenu.hidden) {
    const skills = filteredSkills();
    if (e.key === "ArrowDown") {
      e.preventDefault();
      slashActiveIndex = Math.min(slashActiveIndex + 1, skills.length - 1);
      updateSlashMenu();
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      slashActiveIndex = Math.max(slashActiveIndex - 1, 0);
      updateSlashMenu();
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      closeSlashMenu();
      return;
    }
    if (e.key === "Enter" && !e.shiftKey && skills.length) {
      e.preventDefault();
      attachSkill(skills[slashActiveIndex]);
      return;
    }
    if (e.key === "Tab" && skills.length) {
      e.preventDefault();
      attachSkill(skills[slashActiveIndex]);
      return;
    }
  }

  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (!slashMenu.hidden) return;
  sendMessage(input.value);
});

btnReset.addEventListener("click", resetChat);
btnMindInit.addEventListener("click", () => mindInit(false));
btnMindStep.addEventListener("click", mindStep);
btnQueueEvidence.addEventListener("click", queueEvidence);
btnRunRehearsal.addEventListener("click", runSponsorRehearsal);
btnRunUploadedRehearsal.addEventListener("click", runUploadedRehearsal);
btnLoadWalkthrough.addEventListener("click", () => loadWalkthrough());
btnCopyWalkthroughBrief.addEventListener("click", copyWalkthroughBrief);

setupTabs();

(async function initApp() {
  await loadUiSkills();
  await loadMeta();
  loadGuide();
  if (window.location.pathname === "/walkthrough") {
    showWalkthroughPanel();
  }
  if (skillsLoadError && uiSkills.length) {
    appendMessage("assistant", skillsLoadError, "welcome");
  } else if (skillsLoadError) {
    appendMessage(
      "assistant",
      `Skills could not load: ${skillsLoadError}`,
      "error"
    );
  }
})();
