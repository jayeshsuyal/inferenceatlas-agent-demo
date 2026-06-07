const STORAGE_KEY = "ia_session_id";
const REVIEW_SCOPE_KEY = "ia_review_scope";

const messagesEl = document.getElementById("messages");
const chatView = document.getElementById("chat-view");
const packetView = document.getElementById("packet-view");
const reviewView = document.getElementById("review-view");
const workbenchView = document.getElementById("workbench-view");
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
const workbenchLaneSelect = document.getElementById("workbench-lane-select");
const workbenchFixtureSelect = document.getElementById("workbench-fixture-select");
const btnGenerateWorkbench = document.getElementById("btn-generate-workbench");
const btnCopyWorkbenchBrief = document.getElementById("btn-copy-workbench-brief");
const btnExportWorkbench = document.getElementById("btn-export-workbench");
const workbenchToast = document.getElementById("workbench-toast");
const btnLoadPacket = document.getElementById("btn-load-packet");
const btnCopyPacketBrief = document.getElementById("btn-copy-packet-brief");
const btnExportPacket = document.getElementById("btn-export-packet");
const btnOpenPacketWorkbench = document.getElementById("btn-open-packet-workbench");
const packetLaneSelect = document.getElementById("packet-lane-select");
const packetFixtureSelect = document.getElementById("packet-fixture-select");
const packetToast = document.getElementById("packet-toast");
const packetTitle = document.getElementById("packet-title");
const packetSubtitle = document.getElementById("packet-subtitle");
const packetSummaryCard = document.getElementById("packet-summary-card");
const packetDecisionCard = document.getElementById("packet-decision-card");
const packetVerificationCard = document.getElementById("packet-verification-card");
const packetProofCard = document.getElementById("packet-proof-card");
const packetSponsorCard = document.getElementById("packet-sponsor-card");
const packetDownstreamCard = document.getElementById("packet-downstream-card");
const packetReviewerCard = document.getElementById("packet-reviewer-card");
const packetExportCard = document.getElementById("packet-export-card");
const workbenchTitle = document.getElementById("workbench-title");
const workbenchSubtitle = document.getElementById("workbench-subtitle");
const workbenchIntakeCard = document.getElementById("workbench-intake-card");
const workbenchDecisionCard = document.getElementById("workbench-decision-card");
const workbenchHashCard = document.getElementById("workbench-hash-card");
const workbenchProofCard = document.getElementById("workbench-proof-card");
const workbenchReviewerCard = document.getElementById("workbench-reviewer-card");
const workbenchExportCard = document.getElementById("workbench-export-card");
const btnLoadWalkthrough = document.getElementById("btn-load-walkthrough");
const btnCollectSponsorProof = document.getElementById("btn-collect-sponsor-proof");
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
const walkthroughSubscriberCard = document.getElementById("walkthrough-subscriber-card");
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
const connectorToastEl = document.getElementById("connector-toast");
const btnGithub = document.getElementById("btn-github");
const githubChipsEl = document.getElementById("github-chips");
const githubPicker = document.getElementById("github-picker");
const githubRepoSearch = document.getElementById("github-repo-search");
const githubRepoList = document.getElementById("github-repo-list");
const btnDrive = document.getElementById("btn-drive");
const driveChipsEl = document.getElementById("drive-chips");
const drivePicker = document.getElementById("drive-picker");
const driveFileSearch = document.getElementById("drive-file-search");
const driveFileList = document.getElementById("drive-file-list");
const drivePickerTabs = document.getElementById("drive-picker-tabs");

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

const SUBSCRIBER_LABELS = {
  composio_access_gate: "Composio Access Gate",
  portkey_model_spend_gate: "Portkey Model Spend Gate",
  github_actions_deploy_gate: "GitHub Actions Deploy Gate",
  finance_budget_gate: "Finance Budget Gate",
  security_review_queue: "Security Review Queue",
  datadog_audit_event: "Datadog Audit Event",
};

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
let uiConnectors = [];
let skillsIntro = null;
let connectorsIntro = null;
let connectorsLoadError = null;
let plusMenuState = { skills: false, connectors: false };
let slashActiveIndex = 0;
let slashFilter = "";
let skillsLoadError = null;
let skillsLoaded = false;
let workbenchRegistry = null;
let workbenchResult = null;
let packetDetail = null;
let walkthroughPayload = null;
let walkthroughActiveIndex = 0;
/** @type {Array<{id:string, name:string, slash:string, slash_trigger:string, what_it_proves:string}>} */
let selectedSkills = [];
/** @type {Array<{full_name:string, preview?:string, indexing?:boolean}>} */
let selectedGithubRepos = [];
let githubSearchTimer = null;
/** @type {Array<{file_id:string, name:string, mimeType?:string, media_kind?:string, indexing?:boolean, digest_chars?:number, index_label?:string}>} */
let selectedDriveFiles = [];
let driveSearchTimer = null;
let drivePickerKind = "all";

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
    renderAssistantMarkdown(bubble, text);
    addDownloadButtons(bubble, outputFiles.filter((f) => f.file_id));
  } else {
    bubble.textContent = text;
  }

  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return wrap;
}

function renderAssistantMarkdown(bubble, text) {
  const parts = String(text).split("\n\n");
  parts.forEach((para) => {
    if (!para.trim()) return;
    if (para.startsWith("**") && para.includes("**")) {
      const h = document.createElement("p");
      h.className = "reply-manifest";
      const m = para.match(/^\*\*([^*]+)\*\*\s*(.*)$/s);
      h.innerHTML = m
        ? `<strong>${escapeHtml(m[1])}</strong> ${escapeHtml(m[2] || "")}`
        : escapeHtml(para);
      bubble.appendChild(h);
      return;
    }
    const p = document.createElement("p");
    p.textContent = para.trim();
    bubble.appendChild(p);
  });
  if (!bubble.childNodes.length) {
    const p = document.createElement("p");
    p.textContent = text;
    bubble.appendChild(p);
  }
}

function appendThinkingMessage() {
  const wrap = document.createElement("div");
  wrap.className = "message assistant thinking";
  const bubble = document.createElement("div");
  bubble.className = "bubble thinking-bubble";
  const title = document.createElement("p");
  title.className = "thinking-title";
  title.textContent = "Thinking…";
  const list = document.createElement("ul");
  list.className = "thinking-log";
  bubble.appendChild(title);
  bubble.appendChild(list);
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return { wrap, list };
}

function appendThinkingLine(listEl, line) {
  const li = document.createElement("li");
  li.textContent = line;
  listEl.appendChild(li);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function consumeChatStream(response, thinkingUi) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      let payload;
      try {
        payload = JSON.parse(line.slice(5).trim());
      } catch {
        continue;
      }
      if (payload.type === "thinking" && payload.line && thinkingUi) {
        appendThinkingLine(thinkingUi.list, payload.line);
      } else if (payload.type === "done") {
        return payload;
      } else if (payload.type === "error") {
        throw new Error(payload.detail || "Chat stream failed");
      }
    }
  }
  throw new Error("Stream ended without a reply");
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

function showPacketPanel() {
  document.querySelector('.tab[data-tab="packet"]')?.click();
}

function showWalkthroughPanel() {
  document.querySelector('.tab[data-tab="walkthrough"]')?.click();
}

function showWorkbenchPanel() {
  document.querySelector('.tab[data-tab="workbench"]')?.click();
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

function isGithubSignedIn() {
  const gh = uiConnectors.find((c) => c.id === "github");
  return Boolean(gh && gh.signed_in);
}

function updateGithubToolbar() {
  if (!btnGithub) return;
  btnGithub.hidden = !isGithubSignedIn();
}

function isDriveSignedIn() {
  const dr = uiConnectors.find((c) => c.id === "google_drive");
  return Boolean(dr && dr.signed_in);
}

function updateDriveToolbar() {
  if (!btnDrive) return;
  btnDrive.hidden = !isDriveSignedIn();
}

function closeGithubPicker() {
  if (githubPicker) githubPicker.hidden = true;
}

function openGithubPicker() {
  if (!isGithubSignedIn()) {
    showConnectorToast("GitHub", "Sign in to GitHub first (+ → Connectors).");
    return;
  }
  closeSkillsFlyout();
  closeSlashMenu();
  if (githubPicker) {
    githubPicker.hidden = false;
    if (githubRepoSearch) {
      githubRepoSearch.value = "";
      githubRepoSearch.focus();
    }
    loadGithubRepoList("");
  }
}

async function loadGithubRepoList(query = "") {
  if (!githubRepoList) return;
  githubRepoList.innerHTML = '<p class="github-repo-empty">Loading repositories…</p>';
  try {
    const res = await fetch(
      `/api/connectors/github/repos?session_id=${encodeURIComponent(sessionId)}&q=${encodeURIComponent(query)}`
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Failed to load repos");
    renderGithubRepoList(data.repos || [], Boolean(data.demo));
  } catch (err) {
    githubRepoList.innerHTML = `<p class="github-repo-empty">${escapeHtml(String(err.message || err))}</p>`;
  }
}

function renderGithubRepoList(repos, demo = false) {
  if (!githubRepoList) return;
  githubRepoList.innerHTML = "";
  if (!repos.length) {
    githubRepoList.innerHTML = '<p class="github-repo-empty">No repositories match your search.</p>';
    return;
  }
  if (demo) {
    const note = document.createElement("p");
    note.className = "github-repo-demo-note";
    note.textContent = "Demo list — live repos load after GitHub OAuth sign-in.";
    githubRepoList.appendChild(note);
  }
  repos.forEach((repo) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `github-repo-item${repo.indexed ? " indexed" : ""}`;
    btn.role = "option";
    const attached = selectedGithubRepos.some((r) => r.full_name === repo.full_name);
    btn.innerHTML = `
      <span class="github-repo-item-name">${escapeHtml(repo.full_name)}</span>
      <span class="github-repo-item-meta">${escapeHtml(repo.description || "")}${attached ? " · attached" : ""}${repo.indexed && !attached ? " · indexed" : ""}</span>
    `;
    btn.addEventListener("click", () => attachGithubRepo(repo.full_name));
    githubRepoList.appendChild(btn);
  });
}

async function attachGithubRepo(fullName) {
  if (selectedGithubRepos.some((r) => r.full_name === fullName)) {
    showConnectorToast("GitHub", `${fullName} is already attached.`);
    return;
  }
  selectedGithubRepos.push({ full_name: fullName, indexing: true });
  renderGithubChips();
  closeGithubPicker();
  try {
    const res = await fetch("/api/connectors/github/attach", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, full_name: fullName }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.message || data.detail || "Attach failed");
    const idx = selectedGithubRepos.findIndex((r) => r.full_name === fullName);
    if (idx >= 0) {
      selectedGithubRepos[idx] = {
        full_name: fullName,
        preview: data.preview,
        indexing: false,
        digest_chars: data.digest_chars,
        readme_found: data.readme_found,
        files_included: data.files_included,
        paths_in_tree: data.paths_in_tree,
        sample_paths: data.sample_paths || [],
        index_label: data.message || `Indexed ${fullName}`,
      };
    }
    if (data.file_id) chatAttachmentIds.push(data.file_id);
    renderGithubChips();
    const idxMsg = data.message || `Indexed ${fullName}`;
    showConnectorToast("GitHub", idxMsg, 9000);
    input.focus();
  } catch (err) {
    selectedGithubRepos = selectedGithubRepos.filter((r) => r.full_name !== fullName);
    renderGithubChips();
    showConnectorToast("GitHub", String(err.message || err));
  }
}

function renderGithubChips() {
  if (!githubChipsEl) return;
  githubChipsEl.innerHTML = "";
  if (!selectedGithubRepos.length) {
    githubChipsEl.hidden = true;
    return;
  }
  githubChipsEl.hidden = false;
  selectedGithubRepos.forEach((repo) => {
    const chip = document.createElement("span");
    chip.className = `skill-chip github-repo-chip${repo.indexing ? " indexing" : ""}${repo.digest_chars ? " indexed-ok" : ""}`;
    const link = document.createElement("a");
    link.href = "#";
    link.className = "skill-chip-link";
    if (repo.indexing) {
      link.textContent = `${repo.full_name} …`;
    } else if (repo.digest_chars) {
      const readme = repo.readme_found ? "README ✓" : "no README";
      link.textContent = `${repo.full_name} ✓`;
      link.title =
        repo.index_label ||
        `Indexed ${repo.digest_chars.toLocaleString()} chars · ${readme} · ${repo.files_included || 0} files`;
    } else {
      link.textContent = repo.full_name;
    }
    if (!link.title) link.title = repo.preview || repo.full_name;
    link.addEventListener("click", (e) => e.preventDefault());
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "skill-chip-remove";
    rm.setAttribute("aria-label", `Remove ${repo.full_name}`);
    rm.textContent = "×";
    rm.addEventListener("click", () => detachGithubRepo(repo.full_name));
    chip.appendChild(link);
    chip.appendChild(rm);
    githubChipsEl.appendChild(chip);
  });
}

function detachGithubRepo(fullName) {
  selectedGithubRepos = selectedGithubRepos.filter((r) => r.full_name !== fullName);
  renderGithubChips();
}

function clearSelectedGithubRepos() {
  selectedGithubRepos = [];
  renderGithubChips();
}

function closeDrivePicker() {
  if (drivePicker) drivePicker.hidden = true;
}

function openDrivePicker(kind = "all") {
  if (!isDriveSignedIn()) {
    showConnectorToast("Google Drive", "Sign in to Drive first (+ → Connectors).");
    return;
  }
  closeSkillsFlyout();
  closeSlashMenu();
  closeGithubPicker();
  drivePickerKind = kind;
  if (drivePickerTabs) {
    drivePickerTabs.querySelectorAll(".drive-tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.kind === kind);
    });
  }
  if (drivePicker) {
    drivePicker.hidden = false;
    if (driveFileSearch) {
      driveFileSearch.value = "";
      driveFileSearch.focus();
    }
    loadDriveFileList("", kind);
  }
}

async function loadDriveFileList(query = "", kind = drivePickerKind) {
  if (!driveFileList) return;
  driveFileList.innerHTML = '<p class="github-repo-empty">Loading Drive files…</p>';
  try {
    const res = await fetch(
      `/api/connectors/drive/files?session_id=${encodeURIComponent(sessionId)}&q=${encodeURIComponent(query)}&kind=${encodeURIComponent(kind)}`
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Failed to load Drive files");
    renderDriveFileList(data.files || [], Boolean(data.demo));
  } catch (err) {
    driveFileList.innerHTML = `<p class="github-repo-empty">${escapeHtml(String(err.message || err))}</p>`;
  }
}

function renderDriveFileList(files, demo = false) {
  if (!driveFileList) return;
  driveFileList.innerHTML = "";
  if (!files.length) {
    driveFileList.innerHTML = '<p class="github-repo-empty">No files match your search.</p>';
    return;
  }
  if (demo) {
    const note = document.createElement("p");
    note.className = "github-repo-demo-note";
    note.textContent = "Demo list — live files load after Google Drive OAuth sign-in.";
    driveFileList.appendChild(note);
  }
  files.forEach((file) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "drive-file-item";
    btn.role = "option";
    const attached = selectedDriveFiles.some((f) => f.file_id === file.id);
    const kindLabel = file.media_kind || "file";
    const size = file.size ? `${Math.round(Number(file.size) / 1024)} KB` : "";
    btn.innerHTML = `
      <span class="drive-file-item-name">${escapeHtml(file.name)}</span>
      <span class="drive-file-item-meta">${escapeHtml(kindLabel)}${size ? ` · ${size}` : ""}${attached ? " · attached" : ""}${file.indexed && !attached ? " · indexed" : ""}</span>
    `;
    btn.addEventListener("click", () => attachDriveFile(file.id, file.name, file.mimeType, file.media_kind));
    driveFileList.appendChild(btn);
  });
}

async function attachDriveFile(fileId, name, mimeType, mediaKind) {
  if (selectedDriveFiles.some((f) => f.file_id === fileId)) {
    showConnectorToast("Google Drive", `«${name}» is already attached.`);
    return;
  }
  selectedDriveFiles.push({ file_id: fileId, name: name || fileId, indexing: true, mimeType, media_kind: mediaKind });
  renderDriveChips();
  closeDrivePicker();
  try {
    const res = await fetch("/api/connectors/drive/attach", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, file_id: fileId }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.message || data.detail || "Attach failed");
    const idx = selectedDriveFiles.findIndex((f) => f.file_id === fileId);
    if (idx >= 0) {
      selectedDriveFiles[idx] = {
        file_id: fileId,
        name: data.name || name,
        mimeType: data.mimeType || mimeType,
        media_kind: data.media_kind || mediaKind,
        indexing: false,
        digest_chars: data.digest_chars,
        content_type: data.content_type,
        index_label: data.message,
      };
    }
    if (data.upload_file_id) chatAttachmentIds.push(data.upload_file_id);
    renderDriveChips();
    showConnectorToast("Google Drive", data.message || `Attached ${name}`, 9000);
    input.focus();
  } catch (err) {
    selectedDriveFiles = selectedDriveFiles.filter((f) => f.file_id !== fileId);
    renderDriveChips();
    showConnectorToast("Google Drive", String(err.message || err));
  }
}

function renderDriveChips() {
  if (!driveChipsEl) return;
  driveChipsEl.innerHTML = "";
  if (!selectedDriveFiles.length) {
    driveChipsEl.hidden = true;
    return;
  }
  driveChipsEl.hidden = false;
  selectedDriveFiles.forEach((file) => {
    const chip = document.createElement("span");
    chip.className = `skill-chip drive-repo-chip${file.indexing ? " indexing" : ""}${file.digest_chars ? " indexed-ok" : ""}`;
    const link = document.createElement("a");
    link.href = "#";
    link.className = "skill-chip-link";
    if (file.indexing) {
      link.textContent = `${file.name} …`;
    } else if (file.digest_chars) {
      link.textContent = `${file.name} ✓`;
      link.title = file.index_label || `Indexed ${file.digest_chars.toLocaleString()} chars`;
    } else {
      link.textContent = file.name;
    }
    if (!link.title) link.title = file.name;
    link.addEventListener("click", (e) => e.preventDefault());
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "skill-chip-remove";
    rm.setAttribute("aria-label", `Remove ${file.name}`);
    rm.textContent = "×";
    rm.addEventListener("click", () => detachDriveFile(file.file_id));
    chip.appendChild(link);
    chip.appendChild(rm);
    driveChipsEl.appendChild(chip);
  });
}

function detachDriveFile(fileId) {
  selectedDriveFiles = selectedDriveFiles.filter((f) => f.file_id !== fileId);
  renderDriveChips();
}

function clearSelectedDriveFiles() {
  selectedDriveFiles = [];
  renderDriveChips();
}

if (drivePickerTabs) {
  drivePickerTabs.querySelectorAll(".drive-tab").forEach((tab) => {
    tab.addEventListener("click", (e) => {
      e.stopPropagation();
      drivePickerKind = tab.dataset.kind || "all";
      drivePickerTabs.querySelectorAll(".drive-tab").forEach((t) => {
        t.classList.toggle("active", t === tab);
      });
      loadDriveFileList(driveFileSearch?.value.trim() || "", drivePickerKind);
    });
  });
}

if (btnDrive) {
  btnDrive.addEventListener("click", (e) => {
    e.stopPropagation();
    if (drivePicker && !drivePicker.hidden) closeDrivePicker();
    else openDrivePicker(drivePickerKind);
  });
}

if (driveFileSearch) {
  driveFileSearch.addEventListener("input", () => {
    clearTimeout(driveSearchTimer);
    driveSearchTimer = setTimeout(
      () => loadDriveFileList(driveFileSearch.value.trim(), drivePickerKind),
      280
    );
  });
}

if (btnGithub) {
  btnGithub.addEventListener("click", (e) => {
    e.stopPropagation();
    if (githubPicker && !githubPicker.hidden) closeGithubPicker();
    else openGithubPicker();
  });
}

if (githubRepoSearch) {
  githubRepoSearch.addEventListener("input", () => {
    clearTimeout(githubSearchTimer);
    githubSearchTimer = setTimeout(() => loadGithubRepoList(githubRepoSearch.value.trim()), 280);
  });
}

document.addEventListener("click", (e) => {
  if (githubPicker && !githubPicker.hidden) {
    if (!githubPicker.contains(e.target) && e.target !== btnGithub) {
      closeGithubPicker();
    }
  }
  if (drivePicker && !drivePicker.hidden) {
    if (!drivePicker.contains(e.target) && e.target !== btnDrive) {
      closeDrivePicker();
    }
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

function appendUserMessage(message, skills = [], githubRepos = [], driveFiles = []) {
  clearEmptyProofBoard();
  const wrap = document.createElement("div");
  wrap.className = "message user";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (driveFiles.length) {
    const row = document.createElement("div");
    row.className = "user-skill-chips user-drive-chips";
    driveFiles.forEach((file) => {
      const a = document.createElement("a");
      a.href = "#";
      a.className = "skill-chip-link";
      a.textContent = file.name;
      a.title = file.index_label || file.name;
      a.addEventListener("click", (e) => e.preventDefault());
      row.appendChild(a);
    });
    bubble.appendChild(row);
  }

  if (githubRepos.length) {
    const row = document.createElement("div");
    row.className = "user-skill-chips user-github-chips";
    githubRepos.forEach((repo) => {
      const a = document.createElement("a");
      a.href = "#";
      a.className = "skill-chip-link";
      a.textContent = repo.full_name;
      a.title = repo.preview || "";
      a.addEventListener("click", (e) => e.preventDefault());
      row.appendChild(a);
    });
    bubble.appendChild(row);
  }

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
    .map((s) => s.example_question || SKILL_HINT_BY_ID[s.id])
    .filter(Boolean)
    .slice(0, 2);
  if (!hints.length) {
    hints.push("Summarize what these skills prove and what humans must approve.");
  }
  skillHintsEl.hidden = false;
  skillHintsEl.textContent = `Try asking: ${hints.join(" · ")}`;
}

function showConnectorToast(title, body, ms = 9000) {
  if (!connectorToastEl) return;
  connectorToastEl.innerHTML = `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(body)}</span>`;
  connectorToastEl.hidden = false;
  clearTimeout(showConnectorToast._t);
  showConnectorToast._t = setTimeout(() => {
    connectorToastEl.hidden = true;
  }, ms);
}

function connectorIconClass(icon) {
  const map = {
    gdrive: "G",
    github: "GH",
    nebius: "N",
    tavily: "T",
    composio: "C",
    openclaw: "O",
  };
  return map[icon] || "•";
}

async function refreshConnectors() {
  await loadUiConnectors();
  if (!skillsFlyout.hidden) renderPlusMenu();
}

async function connectConnector(connectorId) {
  try {
    const res = await fetch("/api/connectors/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, connector_id: connectorId }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Connect failed (${res.status})`);

    if (data.mode === "oauth_redirect" && data.redirect_url) {
      window.open(data.redirect_url, "ia_oauth", "width=520,height=720,noopener");
      showConnectorToast("Sign in", "Complete authorization in the popup window…");
      pollConnectorUntilConnected(connectorId);
      return;
    }
    showConnectorToast(connectorId, data.message || "Ready.");
    await refreshConnectors();
  } catch (err) {
    showConnectorToast("Connector", String(err.message || err));
  }
}

async function pollConnectorUntilConnected(connectorId, maxAttempts = 40) {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    try {
      const res = await fetch(
        `/api/connectors/status?session_id=${encodeURIComponent(sessionId)}&connector_id=${encodeURIComponent(connectorId)}`
      );
      const data = await res.json().catch(() => ({}));
      if (data.connection?.status === "connected") {
        showConnectorToast(connectorId, "Signed in — you can import files now.");
        await refreshConnectors();
        return;
      }
    } catch (_) {
      /* retry */
    }
  }
  showConnectorToast(connectorId, "Sign-in still pending — try Import or sign in again.");
}

async function importFromConnector(connectorId, action) {
  try {
    const res = await fetch("/api/connectors/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        connector_id: connectorId,
        action,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (data.needs_sign_in && data.redirect_url) {
      window.open(data.redirect_url, "ia_oauth", "width=520,height=720,noopener");
      showConnectorToast(connectorId, "Sign in first, then import again.");
      pollConnectorUntilConnected(connectorId);
      return;
    }
    if (!res.ok || !data.ok) {
      throw new Error(data.message || data.detail || `Import failed (${res.status})`);
    }
    const attachments = data.attachments || [];
    for (const a of attachments) {
      if (a.file_id) chatAttachmentIds.push(a.file_id);
    }
    if (attachments.length) {
      chatFileChip.hidden = false;
      chatFileChip.classList.remove("error");
      chatFileChip.textContent = `Imported (${connectorId}): ${attachments.map((a) => a.name || a.file_id).join(", ")}`;
      if (data.demo) {
        chatFileChip.title = "Demo fixture — add COMPOSIO_API_KEY + sign in for live Drive/GitHub.";
      }
    }
    showConnectorToast(
      connectorId,
      data.message || `Attached ${attachments.length} file(s) to your next message.`
    );
    closeSkillsFlyout();
    input.focus();
  } catch (err) {
    showConnectorToast("Import", String(err.message || err));
  }
}

window.addEventListener("message", (event) => {
  if (event.data?.type === "connector-oauth") {
    refreshConnectors();
    updateGithubToolbar();
    updateDriveToolbar();
    const msg =
      event.data.message ||
      (event.data.ok ? "Signed in successfully." : "Sign-in failed — see popup for details.");
    showConnectorToast(event.data.connector_id || "Connector", msg, event.data.ok ? 6000 : 14000);
  }
});

function createMenuSection({ id, title, subtitle, blurb, expanded, onToggle, buildBody }) {
  const section = document.createElement("div");
  section.className = "menu-section";

  const header = document.createElement("button");
  header.type = "button";
  header.className = "menu-section-header";
  header.setAttribute("aria-expanded", expanded ? "true" : "false");
  header.innerHTML = `
    <span class="menu-section-chevron" aria-hidden="true">▶</span>
    <span class="menu-section-titles">
      <span class="menu-section-title">${escapeHtml(title)}</span>
      <span class="menu-section-sub">${escapeHtml(subtitle)}</span>
    </span>
  `;

  const body = document.createElement("div");
  body.className = "menu-section-body";
  body.hidden = !expanded;
  if (blurb) {
    const p = document.createElement("p");
    p.className = "menu-section-blurb";
    p.textContent = blurb.replace(/\*\*/g, "");
    body.appendChild(p);
  }
  const inner = document.createElement("div");
  body.appendChild(inner);
  buildBody(inner);

  header.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = body.hidden;
    body.hidden = !open;
    header.setAttribute("aria-expanded", open ? "true" : "false");
    plusMenuState[id] = open;
    onToggle?.(open);
  });

  section.appendChild(header);
  section.appendChild(body);
  return section;
}

function buildSkillMenuRow(skill, onPick) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "plus-menu-item skill-menu-item";
  btn.role = "menuitem";
  const attached = selectedSkills.some((s) => s.id === skill.id);
  const desc = skill.layman_summary || skill.what_it_proves || "";
  btn.innerHTML = `
    <span class="plus-menu-item-icon">${escapeHtml(skill.slash?.[0]?.toUpperCase() || "S")}</span>
    <span class="plus-menu-item-body">
      <span class="plus-menu-item-title">
        <span class="skill-slash">/${escapeHtml(skill.slash)}</span>
        ${escapeHtml(skill.name)}
        ${attached ? '<span class="status-pill connected">On</span>' : ""}
      </span>
      <span class="plus-menu-item-desc">${escapeHtml(desc)}</span>
    </span>
  `;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    onPick(skill);
  });
  return btn;
}

function buildConnectorRow(connector) {
  const wrap = document.createElement("div");
  wrap.className = "connector-row-wrap";

  const row = document.createElement("button");
  row.type = "button";
  row.className = "connector-item plus-menu-item";
  const signLabel = connector.signed_in ? "Signed in" : "Sign in";
  row.innerHTML = `
    <span class="plus-menu-item-icon">${escapeHtml(connectorIconClass(connector.icon))}</span>
    <span class="plus-menu-item-body">
      <span class="plus-menu-item-title">
        ${escapeHtml(connector.name)}
        <span class="status-pill ${escapeHtml(connector.signed_in ? "connected" : connector.status)}">${escapeHtml(connector.signed_in ? "Signed in" : connector.status_label)}</span>
      </span>
      <span class="plus-menu-item-desc">${escapeHtml(connector.layman_summary)}</span>
      <span class="plus-menu-item-desc connector-cta">${escapeHtml(signLabel)} →</span>
    </span>
  `;
  row.addEventListener("click", (e) => {
    e.stopPropagation();
    connectConnector(connector.id);
  });
  wrap.appendChild(row);

  const actions = connector.actions || [];
  if (actions.length) {
    const sub = document.createElement("div");
    sub.className = "connector-submenu-inline";
    for (const action of actions) {
      const ab = document.createElement("button");
      ab.type = "button";
      ab.className = "plus-menu-item connector-import-btn";
      ab.innerHTML = `
        <span class="plus-menu-item-body">
          <span class="plus-menu-item-title">Import: ${escapeHtml(action.label)}</span>
          <span class="plus-menu-item-desc">${escapeHtml(action.layman)}</span>
        </span>
      `;
      ab.addEventListener("click", (e) => {
        e.stopPropagation();
        if (connector.id === "github" && action.id === "repos") {
          if (!connector.signed_in) {
            connectConnector("github").then(() => openGithubPicker());
          } else {
            openGithubPicker();
          }
          closeSkillsFlyout();
          return;
        }
        if (connector.id === "google_drive") {
          const kindMap = { files: "docs", photos: "images", videos: "video" };
          const kind = kindMap[action.id] || "all";
          if (!connector.signed_in) {
            connectConnector("google_drive").then(() => openDrivePicker(kind));
          } else {
            openDrivePicker(kind);
          }
          closeSkillsFlyout();
          return;
        }
        if (!connector.signed_in) {
          connectConnector(connector.id).then(() => importFromConnector(connector.id, action.id));
          return;
        }
        importFromConnector(connector.id, action.id);
      });
      sub.appendChild(ab);
    }
    wrap.appendChild(sub);
  }
  return wrap;
}

function closeConnectorSubmenus() {
  skillsFlyout.querySelectorAll(".connector-submenu").forEach((el) => {
    el.hidden = true;
  });
}

function renderPlusMenu() {
  skillsFlyout.innerHTML = "";
  skillsFlyout.classList.add("plus-menu");

  if (skillsLoadError && !uiSkills.length && !uiConnectors.length) {
    const err = document.createElement("p");
    err.className = "slash-menu-empty";
    err.style.padding = "0.75rem";
    err.textContent = skillsLoadError;
    skillsFlyout.appendChild(err);
    return;
  }

  const intro = document.createElement("div");
  intro.className = "plus-menu-intro";
  intro.innerHTML =
    "<strong>+ Menu</strong> — Skills attach proof for access review. Connectors link external tools (set keys in .env).";
  skillsFlyout.appendChild(intro);

  const skillsBlurb = (skillsIntro?.blurb || "").replace(/\*\*/g, "");
  skillsFlyout.appendChild(
    createMenuSection({
      id: "skills",
      title: skillsIntro?.title || "Skills",
      subtitle: "Access-review proof packs",
      blurb: skillsBlurb,
      expanded: plusMenuState.skills,
      buildBody: (container) => {
        if (!uiSkills.length) {
          const wait = document.createElement("p");
          wait.className = "slash-menu-empty";
          wait.style.padding = "0 0.75rem";
          wait.textContent = "Loading skills…";
          container.appendChild(wait);
          return;
        }
        const sorted = uiSkills
          .slice()
          .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
        for (const skill of sorted) {
          container.appendChild(buildSkillMenuRow(skill, attachSkill));
        }
      },
    })
  );

  const connBlurb = (connectorsIntro?.connectors_blurb || connectorsIntro?.blurb || "").replace(
    /\*\*/g,
    ""
  );
  skillsFlyout.appendChild(
    createMenuSection({
      id: "connectors",
      title: connectorsIntro?.connectors_title || "Connectors",
      subtitle: "Drive, search, integrations",
      blurb: connBlurb,
      expanded: plusMenuState.connectors,
      buildBody: (container) => {
        if (connectorsLoadError && !uiConnectors.length) {
          const err = document.createElement("p");
          err.className = "slash-menu-empty";
          err.style.padding = "0 0.75rem";
          err.textContent = connectorsLoadError;
          container.appendChild(err);
          return;
        }
        if (!uiConnectors.length) {
          const wait = document.createElement("p");
          wait.className = "slash-menu-empty";
          wait.style.padding = "0 0.75rem";
          wait.textContent = "Loading connectors…";
          container.appendChild(wait);
          return;
        }
        for (const c of uiConnectors) {
          container.appendChild(buildConnectorRow(c));
        }
      },
    })
  );
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
  if (!skillsFlyout.hidden) renderPlusMenu();
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
  const github_repos = selectedGithubRepos.filter((r) => !r.indexing).map((r) => r.full_name);
  const drive_file_ids = selectedDriveFiles.filter((f) => !f.indexing).map((f) => f.file_id);
  if ((!message && !skill_ids.length && !github_repos.length && !drive_file_ids.length) || busy) return;

  const skillsSnapshot = selectedSkills.slice();
  const githubSnapshot = selectedGithubRepos.filter((r) => !r.indexing).slice();
  const driveSnapshot = selectedDriveFiles.filter((f) => !f.indexing).slice();
  appendUserMessage(message, skillsSnapshot, githubSnapshot, driveSnapshot);
  input.value = "";
  clearSelectedSkills();
  setBusy(true);

  let thinkingUi = null;
  thinkingUi = appendThinkingMessage();

  try {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        attachment_ids: chatAttachmentIds,
        skill_ids,
        skill_context_position: "prepend",
        github_repos,
        drive_file_ids,
      }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Request failed (${res.status})`);
    }

    const data = await consumeChatStream(res, thinkingUi);
    if (!document.getElementById("panel-metrics")?.hidden) {
      loadSessionMetrics();
    }

    sessionId = data.session_id;
    localStorage.setItem(STORAGE_KEY, sessionId);
    chatStorageScope = `chat_${sessionId}`;
    removeMessage(thinkingUi.wrap);
    appendMessage("assistant", data.reply, "", data.output_files || []);
    chatAttachmentIds = [];
    chatFileChip.hidden = true;
    chatFileChip.classList.remove("error");
  } catch (err) {
    if (thinkingUi?.wrap) removeMessage(thinkingUi.wrap);
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
  clearSelectedGithubRepos();
  clearSelectedDriveFiles();
  closeGithubPicker();
  closeDrivePicker();
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

function setWorkbenchToast(text, isError = false) {
  if (!workbenchToast) return;
  workbenchToast.textContent = text || "";
  workbenchToast.classList.toggle("error", isError);
}

function selectedWorkbenchFixture() {
  return (workbenchRegistry?.fixtures || []).find(
    (fixture) => fixture.fixture_id === workbenchFixtureSelect.value
  );
}

function workbenchUrlFixtureId() {
  const params = new URLSearchParams(window.location.search || "");
  return params.get("fixture") || params.get("scenario") || "";
}

function workbenchShouldAutorun() {
  const params = new URLSearchParams(window.location.search || "");
  return ["1", "true", "yes"].includes((params.get("autorun") || "").toLowerCase());
}

function findWorkbenchFixture(fixtureId) {
  return (workbenchRegistry?.fixtures || []).find((fixture) => fixture.fixture_id === fixtureId);
}

function selectWorkbenchFixture(fixtureId) {
  const fixture = findWorkbenchFixture(fixtureId);
  if (!fixture) return false;
  workbenchLaneSelect.value = fixture.lane_id;
  renderWorkbenchFixtureOptions(fixture.fixture_id);
  workbenchFixtureSelect.value = fixture.fixture_id;
  return true;
}

function renderWorkbenchFixtureOptions(preferredFixtureId = "") {
  if (!workbenchRegistry || !workbenchLaneSelect || !workbenchFixtureSelect) return;
  const laneId = workbenchLaneSelect.value || workbenchRegistry.lanes?.[0]?.lane_id;
  const fixtures = (workbenchRegistry.fixtures || []).filter((fixture) => fixture.lane_id === laneId);
  const currentFixtureId = workbenchFixtureSelect.value;
  workbenchFixtureSelect.innerHTML = "";
  fixtures.forEach((fixture) => {
    const option = document.createElement("option");
    option.value = fixture.fixture_id;
    option.textContent = fixture.label;
    workbenchFixtureSelect.appendChild(option);
  });
  if (fixtures.length) {
    const selected = fixtures.find((fixture) => fixture.fixture_id === preferredFixtureId)
      || fixtures.find((fixture) => fixture.fixture_id === currentFixtureId)
      || fixtures[0];
    workbenchFixtureSelect.value = selected.fixture_id;
  }
}

function applyWorkbenchRegistry(data) {
  workbenchRegistry = data;
  workbenchLaneSelect.innerHTML = "";
  (data.lanes || []).forEach((lane) => {
    const option = document.createElement("option");
    option.value = lane.lane_id;
    option.textContent = lane.label;
    workbenchLaneSelect.appendChild(option);
  });
  const requestedFixtureId = workbenchUrlFixtureId();
  const requestedFixture = (data.fixtures || []).find((fixture) => fixture.fixture_id === requestedFixtureId);
  const defaultFixture = requestedFixture || (data.fixtures || []).find(
    (fixture) => fixture.fixture_id === data.default_fixture_id
  );
  if (defaultFixture) {
    workbenchLaneSelect.value = defaultFixture.lane_id;
  }
  renderWorkbenchFixtureOptions(defaultFixture?.fixture_id || "");
  if (defaultFixture) {
    workbenchFixtureSelect.value = defaultFixture.fixture_id;
  }
}

async function loadWorkbenchRegistry() {
  if (workbenchRegistry) return workbenchRegistry;
  setWorkbenchToast("Loading workbench registry...");
  const res = await fetch("/api/workbench");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Workbench registry failed");
  applyWorkbenchRegistry(data);
  setWorkbenchToast("Workbench registry loaded.");
  return data;
}

function renderWorkbenchList(items, { limit = 5 } = {}) {
  return renderMiniList(items || [], { limit });
}

function renderWorkbenchResult(data) {
  workbenchResult = data;
  const fixture = data.fixture || {};
  const decision = data.decision || {};
  const packet = data.packet_reference || {};
  const local = data.local_verification || {};
  workbenchTitle.textContent = data.title || "Packet Workbench";
  workbenchSubtitle.textContent = fixture.description || "Fixture-only packet generation.";

  workbenchIntakeCard.innerHTML = `
    <span class="eyebrow">Input</span>
    <h3>${escapeHtml(fixture.label || fixture.fixture_id || "Registered fixture")}</h3>
    <p class="walkthrough-summary">${escapeHtml(fixture.description || "")}</p>
    <code class="walkthrough-fact">${escapeHtml(fixture.path || fixture.scenario_name || fixture.fixture_id || "")}</code>
  `;
  const systems = document.createElement("div");
  systems.className = "workbench-list-block";
  systems.innerHTML = `<span class="trace-subhead">Requested systems</span>`;
  systems.appendChild(renderWorkbenchList(data.requested_systems || [], { limit: 6 }));
  workbenchIntakeCard.appendChild(systems);

  workbenchDecisionCard.innerHTML = `
    <span class="eyebrow">Decision</span>
    <h3>${escapeHtml(decision.verdict_class || "review_required")}</h3>
    <div class="walk-metrics">
      <div><span>Production</span><strong>${escapeHtml(String(decision.production_access))}</strong></div>
      <div><span>Grants</span><strong>${escapeHtml(String(decision.permission_grants))}</strong></div>
      <div><span>Writes</span><strong>${escapeHtml(String(decision.external_writes))}</strong></div>
      <div><span>Human review</span><strong>${escapeHtml(String(decision.requires_human_review))}</strong></div>
    </div>
    <p class="walkthrough-summary">${escapeHtml(decision.next_human_action || "")}</p>
  `;

  workbenchHashCard.innerHTML = `
    <span class="eyebrow">Local verification hash</span>
    <h3>Canonical packet hash</h3>
    <p class="walkthrough-summary">Computed locally from the public packet result. No private v1 endpoint is called.</p>
    <code class="walkthrough-fact">${escapeHtml(packet.content_hash || local.content_hash || "")}</code>
    <p class="safety-anchor">v1 call: ${escapeHtml(String(local.calls_v1))} · read-only: ${escapeHtml(String(local.read_only))}</p>
  `;

  workbenchProofCard.innerHTML = `
    <span class="eyebrow">Proof debt</span>
    <h3>Blocked claims and missing proof</h3>
  `;
  const proofGrid = document.createElement("div");
  proofGrid.className = "workbench-proof-grid";
  const blocked = document.createElement("div");
  blocked.innerHTML = `<span class="trace-subhead">Blocked claims</span>`;
  blocked.appendChild(renderWorkbenchList(data.blocked_claims || [], { limit: 5 }));
  const missing = document.createElement("div");
  missing.innerHTML = `<span class="trace-subhead">Missing proof</span>`;
  missing.appendChild(renderWorkbenchList(data.missing_proof || [], { limit: 5 }));
  proofGrid.append(blocked, missing);
  workbenchProofCard.appendChild(proofGrid);

  workbenchReviewerCard.innerHTML = `
    <span class="eyebrow">Reviewer routing</span>
    <h3>${escapeHtml(String((data.reviewer_routing || []).length))} owner gates</h3>
  `;
  workbenchReviewerCard.appendChild(renderWorkbenchList(data.reviewer_routing || [], { limit: 6 }));
  if (data.sponsor_proof_trace) {
    const trace = data.sponsor_proof_trace;
    const traceBox = document.createElement("p");
    traceBox.className = "safety-anchor";
    traceBox.textContent = `Sponsor trace: ${trace.sponsor_order?.join(" -> ") || "locked order"}; decision lock unchanged ${trace.decision_lock_unchanged}.`;
    workbenchReviewerCard.appendChild(traceBox);
  }

  workbenchExportCard.innerHTML = `
    <span class="eyebrow">Export</span>
    <h3>${escapeHtml(data.export_label || "Export workbench result")}</h3>
    <p class="walkthrough-summary">${escapeHtml(data.safety_anchor || "")}</p>
  `;
  const actions = document.createElement("div");
  actions.className = "walk-actions";
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "btn-primary";
  copy.textContent = "Copy review brief";
  copy.addEventListener("click", () => copyWorkbenchBrief());
  const viewHash = document.createElement("button");
  viewHash.type = "button";
  viewHash.className = "btn-ghost";
  viewHash.textContent = "View verification hash";
  viewHash.addEventListener("click", () => setWorkbenchToast(packet.content_hash || "Hash unavailable."));
  const copyVerification = document.createElement("button");
  copyVerification.type = "button";
  copyVerification.className = "btn-ghost";
  copyVerification.textContent = "Copy verification link";
  copyVerification.addEventListener("click", () => copyWorkbenchVerificationLink());
  const openPacket = document.createElement("button");
  openPacket.type = "button";
  openPacket.className = "btn-ghost";
  openPacket.textContent = "Open IA Packet";
  openPacket.addEventListener("click", () => {
    window.location.href = packetDetailUrl(fixture.fixture_id);
  });
  actions.append(copy, openPacket, copyVerification, viewHash);
  workbenchExportCard.appendChild(actions);
  renderArtifactLinks(data.output_files || [], workbenchExportCard);
  btnCopyWorkbenchBrief.disabled = !data.copy_review_brief;
  btnExportWorkbench.disabled = !(data.output_files || []).length;
}

async function generateWorkbench() {
  btnGenerateWorkbench.disabled = true;
  setWorkbenchToast("Generating packet...");
  try {
    if (!workbenchRegistry) await loadWorkbenchRegistry();
    const fixture = selectedWorkbenchFixture();
    if (!fixture) throw new Error("Choose a workbench fixture first.");
    const res = await fetch("/api/workbench/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fixture_id: fixture.fixture_id }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Workbench generation failed");
    renderWorkbenchResult(data);
    setWorkbenchToast("Packet generated. Review brief and export are ready.");
  } catch (err) {
    setWorkbenchToast(String(err.message || err), true);
  } finally {
    btnGenerateWorkbench.disabled = false;
  }
}

async function copyWorkbenchBrief() {
  const text = workbenchResult?.copy_review_brief || "";
  if (!text) {
    setWorkbenchToast("Generate a packet first.", true);
    return;
  }
  let copied = false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      copied = true;
    }
  } catch (_) {
    copied = false;
  }
  if (!copied) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    try {
      copied = document.execCommand("copy");
    } catch (_) {
      copied = false;
    }
    textarea.remove();
  }
  setWorkbenchToast(copied ? "Review brief copied." : "Clipboard unavailable. Use export.", !copied);
}

function workbenchVerificationUrl() {
  const fixtureId = workbenchResult?.fixture?.fixture_id || workbenchFixtureSelect.value || "mcp_tool_blast_radius";
  const url = new URL(window.location.href);
  url.pathname = "/workbench";
  url.search = "";
  url.searchParams.set("fixture", fixtureId);
  url.searchParams.set("autorun", "1");
  return url.toString();
}

async function copyWorkbenchVerificationLink() {
  if (!workbenchResult) {
    setWorkbenchToast("Generate a packet first.", true);
    return;
  }
  const text = workbenchVerificationUrl();
  let copied = false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      copied = true;
    }
  } catch (_) {
    copied = false;
  }
  if (!copied) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    try {
      copied = document.execCommand("copy");
    } catch (_) {
      copied = false;
    }
    textarea.remove();
  }
  setWorkbenchToast(copied ? "Verification link copied." : text, !copied);
}

async function exportWorkbenchResult() {
  const first = (workbenchResult?.output_files || [])[0];
  if (!first?.file_id) {
    setWorkbenchToast("Generate a packet first.", true);
    return;
  }
  try {
    await downloadFile(first.file_id, first.label || "workbench-result.md");
    setWorkbenchToast("Workbench result exported.");
  } catch (err) {
    setWorkbenchToast(String(err.message || err), true);
  }
}

function setPacketToast(text, isError = false) {
  if (!packetToast) return;
  packetToast.textContent = text || "";
  packetToast.classList.toggle("error", isError);
}

function packetSelectedFixtureId() {
  return packetFixtureSelect?.value || packetUrlFixtureId();
}

function packetUrlFixtureId() {
  const params = new URLSearchParams(window.location.search || "");
  return params.get("fixture") || params.get("scenario") || "mcp_tool_blast_radius";
}

function packetShouldAutorun() {
  const params = new URLSearchParams(window.location.search || "");
  return ["1", "true", "yes"].includes((params.get("autorun") || "").toLowerCase());
}

function findPacketFixture(fixtureId) {
  return (workbenchRegistry?.fixtures || []).find((fixture) => fixture.fixture_id === fixtureId);
}

function renderPacketFixtureOptions(preferredFixtureId = "") {
  if (!workbenchRegistry || !packetLaneSelect || !packetFixtureSelect) return;
  const laneId = packetLaneSelect.value || workbenchRegistry.lanes?.[0]?.lane_id;
  const fixtures = (workbenchRegistry.fixtures || []).filter((fixture) => fixture.lane_id === laneId);
  const currentFixtureId = packetFixtureSelect.value;
  packetFixtureSelect.innerHTML = "";
  fixtures.forEach((fixture) => {
    const option = document.createElement("option");
    option.value = fixture.fixture_id;
    option.textContent = fixture.label;
    packetFixtureSelect.appendChild(option);
  });
  if (fixtures.length) {
    const selected = fixtures.find((fixture) => fixture.fixture_id === preferredFixtureId)
      || fixtures.find((fixture) => fixture.fixture_id === currentFixtureId)
      || fixtures[0];
    packetFixtureSelect.value = selected.fixture_id;
  }
}

function applyPacketRegistry(defaultFixtureId = "") {
  if (!workbenchRegistry || !packetLaneSelect || !packetFixtureSelect) return;
  packetLaneSelect.innerHTML = "";
  (workbenchRegistry.lanes || []).forEach((lane) => {
    const option = document.createElement("option");
    option.value = lane.lane_id;
    option.textContent = lane.label;
    packetLaneSelect.appendChild(option);
  });
  const requestedFixtureId = defaultFixtureId || packetUrlFixtureId();
  const requestedFixture = findPacketFixture(requestedFixtureId);
  const defaultFixture = requestedFixture || findPacketFixture(workbenchRegistry.default_fixture_id)
    || (workbenchRegistry.fixtures || [])[0];
  if (defaultFixture) {
    packetLaneSelect.value = defaultFixture.lane_id;
    renderPacketFixtureOptions(defaultFixture.fixture_id);
    packetFixtureSelect.value = defaultFixture.fixture_id;
  }
}

async function loadPacketRegistry(defaultFixtureId = "") {
  await loadWorkbenchRegistry();
  applyPacketRegistry(defaultFixtureId);
  return workbenchRegistry;
}

function packetWorkbenchUrl() {
  const fixtureId = packetDetail?.fixture?.fixture_id || packetSelectedFixtureId();
  const url = new URL(window.location.href);
  url.pathname = "/workbench";
  url.search = "";
  url.searchParams.set("fixture", fixtureId);
  url.searchParams.set("autorun", "1");
  return url.toString();
}

function packetDetailUrl(fixtureId) {
  const url = new URL(window.location.href);
  url.pathname = "/packet";
  url.search = "";
  url.searchParams.set("fixture", fixtureId || "mcp_tool_blast_radius");
  url.searchParams.set("autorun", "1");
  return url.toString();
}

async function copyTextWithFallback(text) {
  let copied = false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      copied = true;
    }
  } catch (_) {
    copied = false;
  }
  if (!copied) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    try {
      copied = document.execCommand("copy");
    } catch (_) {
      copied = false;
    }
    textarea.remove();
  }
  return copied;
}

function renderPacketConsumers(consumers) {
  const wrap = document.createElement("div");
  wrap.className = "workbench-proof-grid";
  (consumers || []).slice(0, 6).forEach((consumer) => {
    const card = document.createElement("div");
    card.className = "packet-consumer";
    card.innerHTML = `
      <span class="trace-subhead">${escapeHtml(consumer.subscriber_category || "consumer")}</span>
      <h4>${escapeHtml(consumer.subscriber || "downstream consumer")}</h4>
      <p>${escapeHtml(consumer.consumer_question || "")}</p>
      <p class="safety-anchor">${escapeHtml(consumer.subscriber_action || "")}</p>
    `;
    wrap.appendChild(card);
  });
  return wrap;
}

function renderPacketDetail(data) {
  packetDetail = data;
  const fixture = data.fixture || {};
  const decision = data.decision || {};
  const packet = data.packet_reference || {};
  const local = data.local_verification || {};
  const trace = data.sponsor_proof_trace || null;
  packetTitle.textContent = data.title || "IA Packet";
  packetSubtitle.textContent = data.definition || "Canonical packet detail.";
  if (fixture.fixture_id) {
    applyPacketRegistry(fixture.fixture_id);
  }

  packetSummaryCard.innerHTML = `
    <span class="eyebrow">Canonical object</span>
    <h3>${escapeHtml(data.product_object || "IA Packet")}</h3>
    <p class="walkthrough-summary">${escapeHtml(data.definition || "")}</p>
    <code class="walkthrough-fact">${escapeHtml(fixture.path || fixture.scenario_name || fixture.fixture_id || "")}</code>
    <p class="safety-anchor">${escapeHtml(data.safety_anchor || "IA did not approve. The next human action is named above.")}</p>
  `;

  packetDecisionCard.innerHTML = `
    <span class="eyebrow">Decision</span>
    <h3>${escapeHtml(decision.verdict_class || "review_required")}</h3>
    <div class="walk-metrics">
      <div><span>Production</span><strong>${escapeHtml(String(decision.production_access))}</strong></div>
      <div><span>Grants</span><strong>${escapeHtml(String(decision.permission_grants))}</strong></div>
      <div><span>Writes</span><strong>${escapeHtml(String(decision.external_writes))}</strong></div>
      <div><span>Human review</span><strong>${escapeHtml(String(decision.requires_human_review))}</strong></div>
    </div>
    <p class="walkthrough-summary">${escapeHtml(decision.next_human_action || "")}</p>
  `;

  packetVerificationCard.innerHTML = `
    <span class="eyebrow">Verification</span>
    <h3>Packet id / revision / hash</h3>
    <code class="walkthrough-fact">${escapeHtml(packet.packet_id || "")}</code>
    <code class="walkthrough-fact">${escapeHtml(packet.revision_id || "")}</code>
    <code class="walkthrough-fact">${escapeHtml(packet.content_hash || local.content_hash || "")}</code>
    <p class="safety-anchor">read-only ${escapeHtml(String(local.read_only))} · v1 call ${escapeHtml(String(local.calls_v1))}</p>
  `;

  packetProofCard.innerHTML = `
    <span class="eyebrow">Proof debt</span>
    <h3>Blocked claims and missing proof</h3>
  `;
  const proofGrid = document.createElement("div");
  proofGrid.className = "workbench-proof-grid";
  const blocked = document.createElement("div");
  blocked.innerHTML = `<span class="trace-subhead">Blocked claims</span>`;
  blocked.appendChild(renderMiniList(data.blocked_claims || [], { limit: 5 }));
  const missing = document.createElement("div");
  missing.innerHTML = `<span class="trace-subhead">Missing proof</span>`;
  missing.appendChild(renderMiniList(data.missing_proof || [], { limit: 5 }));
  proofGrid.append(blocked, missing);
  packetProofCard.appendChild(proofGrid);

  packetSponsorCard.innerHTML = `
    <span class="eyebrow">Sponsor Proof Trace</span>
    <h3>${trace ? escapeHtml(String(trace.step_count)) + " proof steps" : "No live proof step required"}</h3>
    <p class="walkthrough-summary">${trace ? escapeHtml((trace.sponsor_order || []).join(" -> ")) : "Scenario result remains fixture-backed."}</p>
    <p class="safety-anchor">Decision lock unchanged ${escapeHtml(String(trace?.decision_lock_unchanged ?? true))}</p>
  `;

  packetDownstreamCard.innerHTML = `
    <span class="eyebrow">Downstream trust</span>
    <h3>${escapeHtml(String((data.downstream_consumers || []).length))} consumer patterns read the same packet</h3>
    <p class="walkthrough-summary">Gateways, CI, spend controls, review queues, and observability read the packet reference. They cannot approve, mutate, or override it.</p>
  `;
  packetDownstreamCard.appendChild(renderPacketConsumers(data.downstream_consumers || []));

  packetReviewerCard.innerHTML = `
    <span class="eyebrow">Reviewer routing</span>
    <h3>${escapeHtml(String((data.reviewer_routing || []).length))} owner gates</h3>
  `;
  packetReviewerCard.appendChild(renderMiniList(data.reviewer_routing || [], { limit: 6 }));

  packetExportCard.innerHTML = `
    <span class="eyebrow">Export</span>
    <h3>${escapeHtml(data.export_label || "Copy IA Packet brief")}</h3>
    <p class="walkthrough-summary">${escapeHtml(data.workbench_safety_anchor || "")}</p>
  `;
  const actions = document.createElement("div");
  actions.className = "walk-actions";
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "btn-primary";
  copy.textContent = "Copy IA Packet brief";
  copy.addEventListener("click", () => copyPacketBrief());
  const openWorkbench = document.createElement("button");
  openWorkbench.type = "button";
  openWorkbench.className = "btn-ghost";
  openWorkbench.textContent = "Open Workbench";
  openWorkbench.addEventListener("click", () => {
    window.location.href = packetWorkbenchUrl();
  });
  const copyLink = document.createElement("button");
  copyLink.type = "button";
  copyLink.className = "btn-ghost";
  copyLink.textContent = "Copy IA Packet link";
  copyLink.addEventListener("click", async () => {
    const copied = await copyTextWithFallback(packetDetailUrl(fixture.fixture_id));
    setPacketToast(copied ? "IA Packet link copied." : packetDetailUrl(fixture.fixture_id), !copied);
  });
  actions.append(copy, copyLink, openWorkbench);
  packetExportCard.appendChild(actions);
  renderArtifactLinks(data.output_files || [], packetExportCard);
  btnCopyPacketBrief.disabled = !data.copy_review_brief;
  btnExportPacket.disabled = !(data.output_files || []).length;
}

async function loadPacketDetail() {
  btnLoadPacket.disabled = true;
  setPacketToast("Loading IA Packet...");
  try {
    const requestedFixtureId = packetSelectedFixtureId();
    await loadPacketRegistry(requestedFixtureId);
    const fixtureId = packetSelectedFixtureId();
    const res = await fetch(`/api/ia-packet?fixture=${encodeURIComponent(fixtureId)}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "IA Packet load failed");
    renderPacketDetail(data);
    window.history.replaceState({}, "", packetDetailUrl(data.fixture?.fixture_id || fixtureId));
    setPacketToast("IA Packet loaded.");
  } catch (err) {
    setPacketToast(String(err.message || err), true);
  } finally {
    btnLoadPacket.disabled = false;
  }
}

async function copyPacketBrief() {
  const text = packetDetail?.copy_review_brief || "";
  if (!text) {
    setPacketToast("Load an IA Packet first.", true);
    return;
  }
  const copied = await copyTextWithFallback(text);
  setPacketToast(copied ? "IA Packet brief copied." : "Clipboard unavailable. Use export.", !copied);
}

async function exportPacketResult() {
  const first = (packetDetail?.output_files || [])[0];
  if (!first?.file_id) {
    setPacketToast("Load an IA Packet first.", true);
    return;
  }
  try {
    await downloadFile(first.file_id, first.label || "ia-packet.md");
    setPacketToast("IA Packet exported.");
  } catch (err) {
    setPacketToast(String(err.message || err), true);
  }
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

function selectWalkthroughStepById(stepId, toastText = "") {
  if (!walkthroughPayload?.steps) return false;
  const index = walkthroughPayload.steps.findIndex((step) => step.id === stepId);
  if (index < 0) return false;
  walkthroughActiveIndex = index;
  renderWalkthrough(walkthroughPayload);
  if (toastText) setWalkthroughToast(toastText);
  return true;
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

function formatSubscriberName(value) {
  if (SUBSCRIBER_LABELS[value]) return SUBSCRIBER_LABELS[value];
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderSubscriberCard(data) {
  const authority = data.packet_authority || {};
  const rows = data.subscriber_rows || [];
  walkthroughSubscriberCard.innerHTML = `
    <span class="eyebrow">Downstream consumers</span>
    <h3>Systems trust the packet</h3>
    <p class="walkthrough-summary">${escapeHtml(
      authority.headline || "Downstream systems consume the read-only packet authority object."
    )}</p>
    <code class="walkthrough-fact">${escapeHtml(authority.verification_endpoint || "/api/packets/{packet_id}/verification")}</code>
  `;
  const grid = document.createElement("div");
  grid.className = "subscriber-grid";
  rows.slice(0, 6).forEach((item) => {
    const row = document.createElement("article");
    row.className = "subscriber-row";
    row.innerHTML = `
      <div class="subscriber-row-head">
        <span>${escapeHtml(item.category)}</span>
        <strong>${escapeHtml(formatSubscriberName(item.subscriber))}</strong>
      </div>
      <p>${escapeHtml(item.consumer_question)}</p>
      <small>${escapeHtml(item.subscriber_action)} · owner: ${escapeHtml(item.owner)}</small>
      <code>approve ${escapeHtml(String(item.can_approve_access))} · mutate ${escapeHtml(String(item.can_mutate_packet))} · writes ${escapeHtml(String(item.executes_external_writes))}</code>
    `;
    grid.appendChild(row);
  });
  walkthroughSubscriberCard.appendChild(grid);
}

function renderSponsorCard(data) {
  const trace = data.sponsor_proof_trace || {};
  const order = trace.sponsor_order || [];
  walkthroughSponsorCard.innerHTML = `
    <span class="eyebrow">Sponsor proof trace</span>
    <h3>Collect sponsor proof</h3>
    <p class="walkthrough-summary">Locked order: ${escapeHtml(order.join(" -> ") || "Tavily -> Composio -> OpenClaw -> Nebius")}</p>
  `;
  const metrics = document.createElement("div");
  metrics.className = "trace-metrics";
  [
    ["Decision lock", trace.decision_lock_unchanged],
    ["Fallback", trace.all_fallback_used],
    ["Access evidence", trace.access_evidence_present],
    ["Spend evidence", trace.spend_evidence_present],
  ].forEach(([label, value]) => {
    const item = document.createElement("div");
    item.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong>`;
    metrics.appendChild(item);
  });
  walkthroughSponsorCard.appendChild(metrics);

  const traceList = document.createElement("div");
  traceList.className = "trace-step-list";
  (trace.steps || []).forEach((step, index) => {
    const row = document.createElement("article");
    row.className = "trace-step-row";
    row.innerHTML = `
      <strong>${escapeHtml(String(index + 1))}. ${escapeHtml(step.sponsor)} ${escapeHtml(step.verb)}</strong>
      <span>${escapeHtml(step.summary || "")}</span>
      <code>live ${escapeHtml(String(step.used_live_key))} · fallback ${escapeHtml(String(step.fallback_used))} · approve ${escapeHtml(String(step.can_approve_access))}</code>
    `;
    traceList.appendChild(row);
  });
  walkthroughSponsorCard.appendChild(traceList);

  const traceAction = document.createElement("button");
  traceAction.type = "button";
  traceAction.className = "btn-primary btn-block trace-action";
  traceAction.textContent = "Collect sponsor proof";
  traceAction.addEventListener("click", () =>
    selectWalkthroughStepById("sponsor_proof_trace", "Sponsor Proof Trace selected. Decision lock unchanged.")
  );
  walkthroughSponsorCard.appendChild(traceAction);

  const rolesTitle = document.createElement("span");
  rolesTitle.className = "trace-subhead";
  rolesTitle.textContent = "Proof contributors";
  walkthroughSponsorCard.appendChild(rolesTitle);

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
  btnCollectSponsorProof.disabled = !data.sponsor_proof_trace;
  btnCopyWalkthroughBrief.disabled = !data.copy_review_brief;
  renderWalkthroughNav(data);
  renderWalkthroughStrip(data);
  renderActiveWalkthroughCard(data);
  renderDecisionCard(data);
  renderSubscriberCard(data);
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
  if (!text) {
    setWalkthroughToast("Review brief unavailable.", true);
    return;
  }
  let copied = false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      copied = true;
    }
  } catch (_) {
    copied = false;
  }
  if (!copied) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    try {
      copied = document.execCommand("copy");
    } catch (_) {
      copied = false;
    }
    textarea.remove();
  }
  setWalkthroughToast(
    copied ? "Review brief copied." : "Clipboard unavailable. Use PilotMemo export.",
    !copied
  );
}

async function collectSponsorProof() {
  if (!walkthroughPayload?.sponsor_proof_trace) {
    await loadWalkthrough({ silent: true });
  }
  if (!selectWalkthroughStepById("sponsor_proof_trace", "Sponsor Proof Trace selected. Decision lock unchanged.")) {
    setWalkthroughToast("Sponsor Proof Trace unavailable.", true);
  }
}

async function loadSessionMetrics() {
  const metaEl = document.getElementById("metrics-meta");
  const tableWrap = document.getElementById("metrics-table-wrap");
  const eventsEl = document.getElementById("metrics-events");
  if (!metaEl || !tableWrap || !eventsEl || !sessionId) return;
  try {
    const data = await fetch(`/api/session/metrics?session_id=${encodeURIComponent(sessionId)}`).then(
      (r) => r.json()
    );
    metaEl.textContent = `Session ${data.session_id?.slice(0, 8)}… · ${data.llm_provider || "?"} / ${data.llm_model || "?"} · updated ${data.updated_at || "—"}`;
    const b = data.billable || {};
    const rows = [
      ["Demo LLM", `${b.demo_llm?.calls ?? 0} calls`, `${b.demo_llm?.total_tokens ?? 0} tokens`],
      ["Tavily", `${b.tavily?.calls ?? 0} searches`, "—"],
      ["Composio", `${b.composio?.calls ?? 0} calls`, b.composio?.dry_run ? "dry-run" : "live"],
      [
        "v1 HTTP",
        `copilot ${b.v1_http?.copilot_calls ?? 0} · plan ${b.v1_http?.plan_llm_calls ?? 0}`,
        `health ${b.v1_http?.health_calls ?? 0}`,
      ],
      ["GitHub API", `${b.github_api?.index_calls ?? 0} index`, "—"],
      ["Google Drive API", `${b.google_drive_api?.index_calls ?? 0} index`, "—"],
    ];
    tableWrap.innerHTML = `
      <table class="metrics-table">
        <thead><tr><th>Service</th><th>Usage</th><th>Detail</th></tr></thead>
        <tbody>${rows
          .map(
            ([svc, u, d]) =>
              `<tr><td>${escapeHtml(svc)}</td><td>${escapeHtml(String(u))}</td><td>${escapeHtml(String(d))}</td></tr>`
          )
          .join("")}</tbody>
      </table>`;
    eventsEl.innerHTML = "";
    (data.recent_events || [])
      .slice()
      .reverse()
      .slice(0, 24)
      .forEach((ev) => {
        const li = document.createElement("li");
        const svc = ev.service || "?";
        const detail = ev.endpoint || ev.tool || ev.label || ev.action || "";
        li.innerHTML = `<strong>${escapeHtml(svc)}</strong> ${escapeHtml(detail)} <span>${escapeHtml((ev.at || "").slice(11, 19))}</span>`;
        eventsEl.appendChild(li);
      });
    if (!(data.recent_events || []).length) {
      eventsEl.innerHTML = "<li>No billable events yet this session.</li>";
    }
  } catch (err) {
    metaEl.textContent = `Metrics unavailable: ${err.message || err}`;
  }
}

function setupTabs() {
  const tabs = document.querySelectorAll(".sidebar-tabs .tab");
  const panels = {
    start: document.getElementById("panel-start"),
    packet: document.getElementById("panel-packet"),
    workbench: document.getElementById("panel-workbench"),
    walkthrough: document.getElementById("panel-walkthrough"),
    review: document.getElementById("panel-review"),
    metrics: document.getElementById("panel-metrics"),
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
      const isPacket = id === "packet";
      const isWorkbench = id === "workbench";
      const isWalkthrough = id === "walkthrough";
      const isMetrics = id === "metrics";
      chatView.hidden = isReview || isPacket || isWorkbench || isWalkthrough || isMetrics;
      reviewView.hidden = !isReview;
      packetView.hidden = !isPacket;
      workbenchView.hidden = !isWorkbench;
      walkthroughView.hidden = !isWalkthrough;
      if (isReview) {
        await loadGuide();
        await ensureMindsReady();
        await loadMind();
      } else if (isPacket) {
        if (!workbenchRegistry) {
          await loadPacketRegistry();
        } else {
          applyPacketRegistry(packetDetail?.fixture?.fixture_id || packetUrlFixtureId());
        }
        if (packetShouldAutorun() || !packetDetail) {
          await loadPacketDetail();
        }
      } else if (isWorkbench) {
        if (!workbenchRegistry) {
          await loadWorkbenchRegistry();
        }
        const requestedFixtureId = workbenchUrlFixtureId();
        if (requestedFixtureId && selectWorkbenchFixture(requestedFixtureId)) {
          if (workbenchResult?.fixture?.fixture_id !== requestedFixtureId) {
            workbenchResult = null;
          }
        }
        if (workbenchShouldAutorun() || !workbenchResult) {
          await generateWorkbench();
        }
      } else if (isWalkthrough) {
        if (!walkthroughPayload) {
          await loadWalkthrough({ silent: true });
        }
      }
      if (isMetrics) {
        await loadSessionMetrics();
      }
    });
  });

  document.getElementById("btn-refresh-metrics")?.addEventListener("click", () => loadSessionMetrics());
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
    const v1 = health.inferenceatlas_v1 || {};
    const v1Label = v1.configured
      ? v1.ok
        ? "connected"
        : "unreachable"
      : "not set";
    const pills = [
      ["LLM", `${health.llm_provider} · ${health.llm_model}`, health.ok],
      ["v1 engine", v1Label, v1.configured && v1.ok],
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
      let info = health.catalog;
      if (!v1.configured) {
        info += " · Cost engine: set INFERENCEATLAS_V1_URL and run v1 API for rank_configs.";
      } else if (!v1.ok) {
        info += ` · v1 at ${v1.url || "?"} unreachable — using catalog fallback for cost questions.`;
      }
      catalogInfo.textContent = info;
    }

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
    const desc = skill.layman_summary || skill.what_it_proves || "";
    const short = desc.length > 100 ? `${desc.slice(0, 100)}…` : desc;
    btn.innerHTML = `<span class="skill-name">/${escapeHtml(skill.slash)} — ${escapeHtml(skill.name)}</span><span class="skill-meta">${escapeHtml(short)}</span>`;
    btn.addEventListener("mousedown", (e) => {
      e.preventDefault();
      onPick(skill);
    });
    container.appendChild(btn);
  });
}

function renderSkillsFlyout() {
  renderPlusMenu();
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

async function applyConnectorsPayload(data, source) {
  uiConnectors = data.connectors || [];
  connectorsIntro = data.intro || null;
  updateGithubToolbar();
  updateDriveToolbar();
  if (source === "static") {
    connectorsLoadError =
      "Using bundled connectors (restart server: python3 -m web).";
  } else {
    connectorsLoadError = null;
  }
  renderPlusMenu();
}

async function loadUiConnectors() {
  connectorsLoadError = null;
  const q = `?session_id=${encodeURIComponent(sessionId)}`;
  try {
    const res = await fetch(`/api/connectors${q}`);
    if (res.ok) {
      await applyConnectorsPayload(await res.json(), "api");
      return;
    }
    const fb = await fetch("/static/connectors-registry.json");
    if (fb.ok) {
      await applyConnectorsPayload(await fb.json(), "static");
      return;
    }
    throw new Error(
      `Connectors API ${res.status} and bundled registry missing — restart: python3 -m web`
    );
  } catch (err) {
    uiConnectors = [];
    connectorsLoadError = err.message || String(err);
    console.error("connectors load failed", err);
    renderPlusMenu();
  }
}

async function applySkillsPayload(data, source) {
  uiSkills = data.skills || [];
  uiSkillCategories = data.categories || [];
  skillsIntro = data.intro || null;
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
btnLoadPacket.addEventListener("click", loadPacketDetail);
btnCopyPacketBrief.addEventListener("click", copyPacketBrief);
btnExportPacket.addEventListener("click", exportPacketResult);
btnOpenPacketWorkbench.addEventListener("click", () => {
  window.location.href = packetWorkbenchUrl();
});
packetLaneSelect.addEventListener("change", () => {
  renderPacketFixtureOptions();
  packetDetail = null;
  btnCopyPacketBrief.disabled = true;
  btnExportPacket.disabled = true;
  setPacketToast("Lane changed. Load an IA Packet to refresh the product object.");
});
packetFixtureSelect.addEventListener("change", () => {
  packetDetail = null;
  btnCopyPacketBrief.disabled = true;
  btnExportPacket.disabled = true;
  setPacketToast("Fixture changed. Load an IA Packet to refresh the product object.");
});
workbenchLaneSelect.addEventListener("change", () => {
  renderWorkbenchFixtureOptions();
  workbenchResult = null;
  btnCopyWorkbenchBrief.disabled = true;
  btnExportWorkbench.disabled = true;
  setWorkbenchToast("Lane changed. Generate a packet to refresh the result.");
});
workbenchFixtureSelect.addEventListener("change", () => {
  workbenchResult = null;
  btnCopyWorkbenchBrief.disabled = true;
  btnExportWorkbench.disabled = true;
  setWorkbenchToast("Fixture changed. Generate a packet to refresh the result.");
});
btnGenerateWorkbench.addEventListener("click", generateWorkbench);
btnCopyWorkbenchBrief.addEventListener("click", copyWorkbenchBrief);
btnExportWorkbench.addEventListener("click", exportWorkbenchResult);
btnLoadWalkthrough.addEventListener("click", () => loadWalkthrough());
btnCollectSponsorProof.addEventListener("click", collectSponsorProof);
btnCopyWalkthroughBrief.addEventListener("click", copyWalkthroughBrief);

setupTabs();

(async function initApp() {
  await Promise.all([loadUiSkills(), loadUiConnectors()]);
  await loadMeta();
  loadGuide();
  if (window.location.pathname === "/workbench") {
    showWorkbenchPanel();
  }
  if (window.location.pathname === "/packet") {
    showPacketPanel();
  }
  if (window.location.pathname === "/walkthrough") {
    showWalkthroughPanel();
  }
  if (connectorsLoadError && uiConnectors.length) {
    appendMessage("assistant", connectorsLoadError, "welcome");
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
