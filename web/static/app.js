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
const composerShell = document.getElementById("composer-shell");
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
const btnExportPortkeyGate = document.getElementById("btn-export-portkey-gate");
const btnOpenPacketWorkbench = document.getElementById("btn-open-packet-workbench");
const packetLaneSelect = document.getElementById("packet-lane-select");
const packetFixtureSelect = document.getElementById("packet-fixture-select");
const packetToast = document.getElementById("packet-toast");
const packetTitle = document.getElementById("packet-title");
const packetSubtitle = document.getElementById("packet-subtitle");
const packetReviewSteps = Array.from(document.querySelectorAll("[data-packet-target]"));
const packetSummaryCard = document.getElementById("packet-summary-card");
const packetDecisionCard = document.getElementById("packet-decision-card");
const packetVerificationCard = document.getElementById("packet-verification-card");
const packetProofCard = document.getElementById("packet-proof-card");
const packetSponsorCard = document.getElementById("packet-sponsor-card");
const packetDownstreamCard = document.getElementById("packet-downstream-card");
const packetTeamCard = document.getElementById("packet-team-card");
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
const packetCoachQuickChips = document.getElementById("packet-coach-quick-chips");
const packetCoachStatus = document.getElementById("packet-coach-status");
const packetInlineCoachPrompts = document.getElementById("packet-inline-coach-prompts");
const packetInlineCoachStatus = document.getElementById("packet-inline-coach-status");
const packetInlineCoachOutput = document.getElementById("packet-inline-coach-output");
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
const repoProofCockpit = document.getElementById("repo-proof-cockpit");
const btnRunRepoProof = document.getElementById("btn-run-repo-proof");
const btnExportRepoBrief = document.getElementById("btn-export-repo-brief");
const btnRootConnectGithub = document.getElementById("btn-root-connect-github");
const btnRootDemoGithub = document.getElementById("btn-root-demo-github");
const repoConnectStatus = document.getElementById("repo-connect-status");
const repoInlinePicker = document.getElementById("repo-inline-picker");
const repoInlineSearch = document.getElementById("repo-inline-search");
const repoInlineList = document.getElementById("repo-inline-list");
const repoIndexSummary = document.getElementById("repo-index-summary");
const repoSelectedName = document.getElementById("repo-selected-name");
const repoIndexedState = document.getElementById("repo-indexed-state");
const repoReviewRunId = document.getElementById("repo-review-run-id");
const repoRequestRepoName = document.getElementById("repo-request-repo-name");
const repoCoachRead = document.getElementById("repo-coach-read");
const repoCockpitVerdict = document.getElementById("repo-cockpit-verdict");
const repoCockpitStatus = document.getElementById("repo-cockpit-status");
const repoProofResult = document.getElementById("repo-proof-result");
const repoNextActionCard = document.getElementById("repo-next-action-card");
const repoProofResolutionCard = document.getElementById("repo-proof-resolution-card");
const repoSponsorProofCard = document.getElementById("repo-sponsor-proof-card");
const repoPortkeyCard = document.getElementById("repo-portkey-card");

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
  ["1 · Attach repo", "Use demo-support-incidents."],
  ["2 · Run IA", "Generate the packet-backed review."],
  ["3 · Act", "Follow the one named human action."],
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
let packetPortkeyPreview = null;
let packetPortkeyProofLoop = null;
let packetInlineCoachBusy = false;
let walkthroughPayload = null;
let walkthroughSponsorRun = null;
let walkthroughSponsorLedgerRecord = null;
let walkthroughActiveIndex = 0;
let runtimeHealth = null;
let currentReviewRun = null;
/** @type {Array<{id:string, name:string, slash:string, slash_trigger:string, what_it_proves:string}>} */
let selectedSkills = [];
/** @type {Array<{full_name:string, preview?:string, indexing?:boolean}>} */
let selectedGithubRepos = [];
let githubSearchTimer = null;
let rootRepoSearchTimer = null;
/** @type {Array<{file_id:string, name:string, mimeType?:string, media_kind?:string, indexing?:boolean, digest_chars?:number, index_label?:string}>} */
let selectedDriveFiles = [];
let driveSearchTimer = null;
let drivePickerKind = "all";

const REPO_PROOF_FIXTURE = "support_triage_agent";
const DEFAULT_REVIEW_ACCESS_REQUEST =
  "support-triage-bot needs to read issues, comment, and create labels.";
const DEFAULT_REVIEW_PROOF_ITEMS = [
  { id: "repo_owner_approval", label: "Repo owner approval" },
  { id: "rollback_offswitch", label: "Rollback/off-switch proof" },
  { id: "environment_boundary", label: "Environment boundary" },
];
const FIRST_RUN_PACKET_URL = "/packet?fixture=support_triage_agent&autorun=1";
const FIRST_RUN_HEADING =
  "Review GitHub access for an AI agent";
const FIRST_RUN_BODY =
  "Use the demo repo request. IA builds a packet, names the human action, previews Portkey, and opens ProofGraph without writes.";
const FIRST_RUN_COACH_STATUS =
  "Run the repo access review first; Ask IA answers from the packet, not raw agent intent.";

function setBusy(loading) {
  busy = loading;
  btnSend.disabled = loading;
  input.disabled = loading;
  btnSend.querySelector(".send-label").hidden = loading;
  btnSend.querySelector(".spinner").hidden = !loading;
  if (packetCoachQuickChips) {
    packetCoachQuickChips.setAttribute("aria-busy", String(loading));
    packetCoachQuickChips.dataset.busy = String(loading);
    packetCoachQuickChips
      .querySelectorAll("button[data-ask-prompt]")
      .forEach((button) => {
        button.disabled = loading;
        button.setAttribute("aria-disabled", String(loading));
      });
  }
  if (packetCoachStatus) {
    if (loading) {
      packetCoachStatus.hidden = false;
      packetCoachStatus.textContent =
        "Answering... packet-backed quick prompts are paused.";
    } else if (composerShell?.classList.contains("first-run-locked")) {
      packetCoachStatus.hidden = false;
      packetCoachStatus.textContent = FIRST_RUN_COACH_STATUS;
    } else {
      packetCoachStatus.hidden = true;
      packetCoachStatus.textContent = "";
    }
  }
}

function lockPacketCoach() {
  composerShell?.classList.add("first-run-locked");
  if (packetCoachStatus) {
    packetCoachStatus.hidden = false;
    packetCoachStatus.textContent = FIRST_RUN_COACH_STATUS;
  }
}

function unlockPacketCoach() {
  composerShell?.classList.remove("first-run-locked");
  if (packetCoachStatus && !busy) {
    packetCoachStatus.hidden = true;
    packetCoachStatus.textContent = "";
  }
}

function setPacketInlineCoachBusy(loading) {
  packetInlineCoachBusy = loading;
  packetInlineCoachPrompts
    ?.querySelectorAll("button[data-ask-prompt]")
    .forEach((button) => {
      button.disabled = loading;
      button.setAttribute("aria-disabled", String(loading));
    });
}

function setPacketInlineCoachStatus(text, isError = false) {
  if (!packetInlineCoachStatus) return;
  packetInlineCoachStatus.textContent = text || "";
  packetInlineCoachStatus.classList.toggle("error", isError);
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

function downloadJsonPayload(payload, label) {
  const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = (label || "ia-packet-export.json").replace(/[^\w.\-]+/g, "_");
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

function renderFirstRunWelcome() {
  const wrap = document.createElement("div");
  wrap.className = "message assistant welcome";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const eyebrow = document.createElement("p");
  eyebrow.className = "first-run-eyebrow";
  eyebrow.textContent = "Review in 90 seconds";

  const heading = document.createElement("h2");
  heading.textContent = FIRST_RUN_HEADING;

  const body = document.createElement("p");
  body.textContent = FIRST_RUN_BODY;

  const actions = document.createElement("div");
  actions.className = "first-run-actions";

  const packetLink = document.createElement("a");
  packetLink.className = "btn-primary first-run-cta";
  packetLink.href = FIRST_RUN_PACKET_URL;
  packetLink.textContent = "Inspect packet";

  actions.append(packetLink);
  bubble.append(eyebrow, heading, body, actions);
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return wrap;
}

function renderAssistantMarkdown(bubble, text) {
  if (renderPacketCoachReply(bubble, text)) {
    return;
  }
  const parts = String(text).split("\n\n");
  parts.forEach((para) => {
    const trimmed = para.trim();
    if (!trimmed) return;
    if (trimmed.startsWith("## ")) {
      const lines = trimmed.split("\n").map((line) => line.trim()).filter(Boolean);
      const heading = document.createElement("p");
      heading.className = "reply-section-heading";
      heading.textContent = lines.shift().replace(/^##\s+/, "");
      bubble.appendChild(heading);
      if (lines.length) {
        renderReplyLines(bubble, lines);
      }
      return;
    }
    if (trimmed.startsWith("- ")) {
      renderReplyLines(bubble, trimmed.split("\n").map((line) => line.trim()).filter(Boolean));
      return;
    }
    if (trimmed.startsWith("**") && trimmed.includes("**")) {
      const h = document.createElement("p");
      h.className = "reply-manifest";
      const m = trimmed.match(/^\*\*([^*]+)\*\*\s*(.*)$/s);
      h.innerHTML = m
        ? `<strong>${escapeHtml(m[1])}</strong> ${escapeHtml(m[2] || "")}`
        : escapeHtml(trimmed);
      bubble.appendChild(h);
      return;
    }
    const p = document.createElement("p");
    p.textContent = trimmed;
    bubble.appendChild(p);
  });
  if (!bubble.childNodes.length) {
    const p = document.createElement("p");
    p.textContent = text;
    bubble.appendChild(p);
  }
}

function parsePacketCoachReply(text) {
  const raw = String(text || "");
  if (!raw.includes("Packet-backed chat: shared CLI/API truth")) {
    return null;
  }
  const lines = raw.split("\n").map((line) => line.trim());
  const reply = {
    context: "",
    currentRead: "",
    topBlocker: "",
    nextHumanAction: "",
    proofQuestion: "",
    inspectLabel: "",
    inspectPath: "",
    source: "",
    safety: "",
    preview: [],
  };
  const contextMatch = raw.match(/^\*\*Context used\*\*\s+—\s+(.+)$/m);
  if (contextMatch) {
    reply.context = contextMatch[1].trim();
  }
  let section = "";
  for (const line of lines) {
    if (!line) continue;
    if (line === "## Current read") {
      section = "current";
      continue;
    }
    if (line === "## Portkey preview") {
      section = "preview";
      continue;
    }
    if (line.startsWith("## ")) {
      section = "";
      continue;
    }
    const field = line.match(/^\*\*([^*]+):\*\*\s*(.+)$/);
    if (field) {
      const key = field[1].trim();
      const value = field[2].trim();
      if (key === "Top blocker") reply.topBlocker = value;
      if (key === "Next human action") reply.nextHumanAction = value;
      if (key === "One proof question") reply.proofQuestion = value;
      if (key === "Source") reply.source = value;
      if (key === "Inspect") {
        const inspect = value.match(/^(.+?)\s+-\s+`([^`]+)`$/);
        reply.inspectLabel = inspect ? inspect[1].trim() : value;
        reply.inspectPath = inspect ? inspect[2].trim() : "";
      }
      section = "";
      continue;
    }
    if (section === "current" && !reply.currentRead) {
      reply.currentRead = line;
      continue;
    }
    if (section === "preview" && line.startsWith("- ")) {
      reply.preview.push(line.replace(/^-\s+/, ""));
      continue;
    }
    if (line.includes("IA does not approve")) {
      reply.safety = line;
    }
  }
  return reply.currentRead ? reply : null;
}

function renderCoachFact(label, value, tone = "") {
  const item = document.createElement("div");
  item.className = `coach-fact ${tone}`.trim();
  const key = document.createElement("span");
  key.textContent = label;
  const val = document.createElement("strong");
  val.textContent = value || "Not available";
  item.append(key, val);
  return item;
}

function renderPacketCoachReply(bubble, text) {
  const reply = parsePacketCoachReply(text);
  if (!reply) return false;
  bubble.classList.add("packet-coach-bubble");

  const card = document.createElement("article");
  card.className = "packet-coach-answer";

  const head = document.createElement("div");
  head.className = "coach-answer-head";
  const label = document.createElement("span");
  label.className = "coach-answer-label";
  label.textContent = "Ask IA";
  const title = document.createElement("h3");
  title.textContent = "Packet-backed decision coach";
  const badges = document.createElement("div");
  badges.className = "coach-answer-badges";
  ["Read-only", "No approval", "No write"].forEach((value) => {
    const badge = document.createElement("span");
    badge.textContent = value;
    badges.appendChild(badge);
  });
  head.append(label, title, badges);

  const read = document.createElement("p");
  read.className = "coach-current-read";
  read.textContent = reply.currentRead;

  const facts = document.createElement("div");
  facts.className = "coach-facts";
  facts.append(
    renderCoachFact("Decision", "Blocked", "danger"),
    renderCoachFact("Movement", "Human review", "warn"),
    renderCoachFact("Truth source", "IA Packet", "success")
  );

  const body = document.createElement("div");
  body.className = "coach-answer-body";
  body.append(
    renderCoachFact("Top blocker", reply.topBlocker, "wide"),
    renderCoachFact("Next human action", reply.nextHumanAction, "wide"),
    renderCoachFact("One proof question", reply.proofQuestion, "wide")
  );

  const actions = document.createElement("div");
  actions.className = "coach-answer-actions";
  if (reply.inspectLabel) {
    const inspect = document.createElement("a");
    inspect.className = "coach-inspect-link";
    inspect.href = reply.inspectPath || "#";
    inspect.textContent = reply.inspectLabel;
    actions.appendChild(inspect);
  }
  if (reply.preview.length) {
    const preview = document.createElement("div");
    preview.className = "coach-preview";
    reply.preview.forEach((line) => {
      const chip = document.createElement("span");
      chip.textContent = line.replace(/`/g, "");
      preview.appendChild(chip);
    });
    actions.appendChild(preview);
  }

  const safety = document.createElement("p");
  safety.className = "coach-safety-anchor";
  safety.textContent =
    reply.safety || "IA does not approve this request. Human review is required and unsafe movement stays blocked.";

  const details = document.createElement("details");
  details.className = "coach-source-details";
  const summary = document.createElement("summary");
  summary.textContent = "Packet reference";
  const source = document.createElement("code");
  source.textContent = reply.source || reply.context || "Packet-backed chat";
  details.append(summary, source);

  card.append(head, read, facts, body, actions, safety, details);
  bubble.appendChild(card);
  return true;
}

function renderReplyLines(bubble, lines) {
  let list = null;
  lines.forEach((line) => {
    if (line.startsWith("- ")) {
      if (!list) {
        list = document.createElement("ul");
        list.className = "reply-list";
        bubble.appendChild(list);
      }
      const item = document.createElement("li");
      item.textContent = line.replace(/^-\s+/, "");
      list.appendChild(item);
      return;
    }
    list = null;
    const p = document.createElement("p");
    p.textContent = line;
    bubble.appendChild(p);
  });
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
  updateReviewRepoConnectUi();
}

function selectedReviewRepo() {
  return selectedGithubRepos.find((repo) => !repo.indexing && repo.digest_chars) || null;
}

function isReviewRepoReady() {
  const repo = selectedReviewRepo();
  return Boolean(
    repo &&
      currentReviewRun &&
      currentReviewRun.stage === "repo_selected" &&
      currentReviewRun.selected_repo?.full_name === repo.full_name
  );
}

function setRepoConnectStatus(message, error = false) {
  if (!repoConnectStatus) return;
  repoConnectStatus.textContent = message;
  repoConnectStatus.classList.toggle("error", error);
}

function updateReviewCtaState() {
  if (!btnRunRepoProof) return;
  const loading = btnRunRepoProof.dataset.loading === "true";
  btnRunRepoProof.disabled = loading || !isReviewRepoReady();
  btnRunRepoProof.textContent = loading ? "Reviewing access..." : "Review access";
  if (repoCockpitStatus && !loading && repoProofCockpit?.dataset.loaded !== "true") {
    repoCockpitStatus.classList.remove("error");
    repoCockpitStatus.textContent = isReviewRepoReady()
      ? "Repo connected and indexed. Ready to generate the packet."
      : "Connect and index one repo before generating a packet.";
  }
}

function updateReviewRepoConnectUi() {
  const signedIn = isGithubSignedIn();
  if (btnRootConnectGithub) {
    btnRootConnectGithub.textContent = signedIn ? "Choose repo" : "Connect GitHub";
  }
  if (btnRootDemoGithub) {
    btnRootDemoGithub.hidden = false;
  }
  updateReviewCtaState();
}

function renderReviewRepoSummary(repo = null) {
  if (!repoIndexSummary) return;
  const selected = repo || selectedReviewRepo();
  repoIndexSummary.hidden = !selected;
  if (!selected) {
    if (repoRequestRepoName) repoRequestRepoName.textContent = "Choose a GitHub repo first.";
    if (repoCoachRead) {
      repoCoachRead.textContent =
        "Connect GitHub or use the demo repo. IA will answer from the current ReviewRun, not raw agent intent.";
    }
    return;
  }
  if (repoSelectedName) {
    repoSelectedName.textContent = selected.full_name;
  }
  if (repoRequestRepoName) {
    repoRequestRepoName.textContent = selected.full_name;
  }
  if (repoIndexedState) {
    if (selected.indexing) {
      repoIndexedState.textContent = "Indexing...";
    } else {
      const files = selected.files_included ?? 0;
      const chars = selected.digest_chars ? selected.digest_chars.toLocaleString() : "0";
      repoIndexedState.textContent = `Indexed · ${chars} chars · ${files} files`;
    }
  }
  if (repoReviewRunId) {
    repoReviewRunId.textContent = currentReviewRun?.run_id || "Creating...";
  }
  if (repoCoachRead) {
    repoCoachRead.textContent = selected.indexing
      ? `Indexing ${selected.full_name}. IA cannot generate the packet until this repo is ready.`
      : `${selected.full_name} is indexed. Next human action: run the access review to generate a packet.`;
  }
  updateReviewCtaState();
}

function closeReviewRepoPicker() {
  if (repoInlinePicker) repoInlinePicker.hidden = true;
}

function renderReviewRepoList(repos, demo = false) {
  if (!repoInlineList) return;
  repoInlineList.innerHTML = "";
  if (!repos.length) {
    repoInlineList.innerHTML = '<p class="github-repo-empty">No repositories match your search.</p>';
    return;
  }
  if (demo) {
    const note = document.createElement("p");
    note.className = "github-repo-demo-note";
    note.textContent = "Demo list. Select one repo; IA indexes only that repo for this ReviewRun.";
    repoInlineList.appendChild(note);
  }
  repos.forEach((repo) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `repo-inline-item${repo.indexed ? " indexed" : ""}`;
    btn.role = "option";
    btn.innerHTML = `
      <span class="github-repo-item-name">${escapeHtml(repo.full_name)}</span>
      <span class="github-repo-item-meta">${escapeHtml(repo.description || "")}${repo.private ? " · private" : ""}${repo.indexed ? " · indexed" : ""}</span>
    `;
    btn.addEventListener("click", () => attachReviewRepo(repo));
    repoInlineList.appendChild(btn);
  });
}

async function loadReviewRepoList(query = "") {
  if (!repoInlineList || !repoInlinePicker) return;
  if (!isGithubSignedIn()) {
    setRepoConnectStatus("Connect GitHub or use the demo repo before choosing a repository.");
    return;
  }
  repoInlinePicker.hidden = false;
  repoInlineList.innerHTML = '<p class="github-repo-empty">Loading repositories...</p>';
  try {
    const res = await fetch(
      `/api/connectors/github/repos?session_id=${encodeURIComponent(sessionId)}&q=${encodeURIComponent(query)}`
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.message || data.detail || "Failed to load repos");
    renderReviewRepoList(data.repos || [], Boolean(data.demo));
    setRepoConnectStatus(
      data.demo
        ? "Demo GitHub connected. Choose one repo to index."
        : "GitHub connected. Choose one repo to index."
    );
  } catch (err) {
    repoInlineList.innerHTML = `<p class="github-repo-empty">${escapeHtml(String(err.message || err))}</p>`;
    setRepoConnectStatus(String(err.message || err), true);
  }
}

async function createReviewRunForIndexedRepo(repo) {
  const res = await fetch("/api/review-runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      selected_repo: {
        provider: "github",
        full_name: repo.full_name,
        source: repo.demo ? "demo_repo" : "github_connector",
      },
      repo_index_summary: {
        status: repo.digest_chars ? "indexed" : "ready",
        indexed_repo_count: 1,
        digest_chars: repo.digest_chars || 0,
        readme_found: Boolean(repo.readme_found),
        files_included: repo.files_included || 0,
        paths_in_tree: repo.paths_in_tree || 0,
        sample_paths: repo.sample_paths || [],
        index_label: repo.index_label || `Indexed ${repo.full_name}`,
      },
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.ok) throw new Error(data.detail || "ReviewRun creation failed");
  currentReviewRun = data.run;
  return currentReviewRun;
}

async function attachReviewRepo(repo) {
  const fullName = repo.full_name;
  currentReviewRun = null;
  selectedGithubRepos = [{ full_name: fullName, indexing: true, demo: Boolean(repo.demo) }];
  renderGithubChips();
  renderReviewRepoSummary(selectedGithubRepos[0]);
  closeReviewRepoPicker();
  setRepoConnectStatus(`Indexing ${fullName}...`);
  try {
    const res = await fetch("/api/connectors/github/attach", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, full_name: fullName }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.message || data.detail || "Attach failed");
    const indexedRepo = {
      full_name: fullName,
      preview: data.preview,
      indexing: false,
      demo: Boolean(repo.demo),
      digest_chars: data.digest_chars,
      readme_found: data.readme_found,
      files_included: data.files_included,
      paths_in_tree: data.paths_in_tree,
      sample_paths: data.sample_paths || [],
      index_label: data.message || `Indexed ${fullName}`,
    };
    selectedGithubRepos = [indexedRepo];
    if (data.file_id && !chatAttachmentIds.includes(data.file_id)) {
      chatAttachmentIds.push(data.file_id);
    }
    await createReviewRunForIndexedRepo(indexedRepo);
    renderGithubChips();
    renderReviewRepoSummary(indexedRepo);
    setRepoConnectStatus(`Repo connected and indexed: ${fullName}. ReviewRun is ready.`);
    showConnectorToast("GitHub", data.message || `Indexed ${fullName}`, 9000);
  } catch (err) {
    selectedGithubRepos = [];
    currentReviewRun = null;
    renderGithubChips();
    renderReviewRepoSummary(null);
    setRepoConnectStatus(String(err.message || err), true);
  } finally {
    updateReviewCtaState();
  }
}

async function beginRootGithubConnect() {
  if (isGithubSignedIn()) {
    await loadReviewRepoList("");
    return;
  }
  setRepoConnectStatus("Opening GitHub sign-in. Use demo repo if OAuth is not configured.");
  await connectConnector("github");
}

async function useDemoGithubForReview() {
  setRepoConnectStatus("Starting demo GitHub session...");
  try {
    const body = new URLSearchParams({ demo: "1" });
    const res = await fetch(
      `/api/connectors/oauth/popup/github?session_id=${encodeURIComponent(sessionId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      }
    );
    if (!res.ok) throw new Error(`Demo sign-in failed (${res.status})`);
    await refreshConnectors();
    await loadReviewRepoList("");
  } catch (err) {
    setRepoConnectStatus(String(err.message || err), true);
  }
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

if (btnRootConnectGithub) {
  btnRootConnectGithub.addEventListener("click", () => beginRootGithubConnect());
}

if (btnRootDemoGithub) {
  btnRootDemoGithub.addEventListener("click", () => useDemoGithubForReview());
}

if (repoInlineSearch) {
  repoInlineSearch.addEventListener("input", () => {
    clearTimeout(rootRepoSearchTimer);
    rootRepoSearchTimer = setTimeout(() => loadReviewRepoList(repoInlineSearch.value.trim()), 280);
  });
}

document.addEventListener("click", (e) => {
  if (githubPicker && !githubPicker.hidden) {
    if (!githubPicker.contains(e.target) && e.target !== btnGithub) {
      closeGithubPicker();
    }
  }
  if (repoInlinePicker && !repoInlinePicker.hidden) {
    const clickedRootConnect =
      e.target === btnRootConnectGithub || e.target === btnRootDemoGithub;
    if (!repoInlinePicker.contains(e.target) && !clickedRootConnect) {
      closeReviewRepoPicker();
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
    if (event.data.ok && event.data.connector_id === "github") {
      loadReviewRepoList("");
    }
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

  unlockPacketCoach();
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
        current_fixture: currentPacketFixtureForChat(),
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
  lockPacketCoach();
  messagesEl.innerHTML = "";
  renderFirstRunWelcome();
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

function currentPacketFixtureForChat() {
  const params = new URLSearchParams(window.location.search || "");
  const urlFixture = params.get("fixture") || params.get("scenario") || "";
  if (packetDetail?.fixture?.fixture_id) return packetDetail.fixture.fixture_id;
  if (window.location.pathname === "/packet" && urlFixture) return urlFixture;
  return "";
}

function setupPacketReviewRail() {
  packetReviewSteps.forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.packetTarget || "");
      if (!target) return;
      packetReviewSteps.forEach((step) => {
        step.classList.remove("active");
        step.removeAttribute("aria-current");
      });
      button.classList.add("active");
      button.setAttribute("aria-current", "step");
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function markPacketReviewRailLoaded() {
  packetReviewSteps.forEach((button) => {
    button.classList.add("ready");
    button.removeAttribute("aria-disabled");
  });
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

function packetPortkeyPreviewPath(fixtureId) {
  return `/api/packets/${encodeURIComponent(fixtureId || "ai_spend_budget_overrun")}/downstream/portkey?mode=dry-run`;
}

function packetPortkeyProofLoopPath(fixtureId, requestedMode = "model_request") {
  return `/api/packets/${encodeURIComponent(fixtureId || "ai_spend_budget_overrun")}/downstream/portkey/proof-loop?requested_mode=${encodeURIComponent(requestedMode)}`;
}

function proofGraphUrl() {
  return "/proofgraph";
}

function packetPortkeyExportName(payload) {
  const packetId = payload?.ia_packet_reference?.packet_id || packetDetail?.fixture?.fixture_id || "ia_packet";
  return `${packetId}.portkey_gate.dry_run.json`;
}

function verdictTone(decision = {}) {
  if (decision.verdict_class === "ready_with_gates") {
    return "approved";
  }
  if (decision.approval_granted || decision.production_access || decision.permission_grants) {
    return "approved";
  }
  if (decision.requires_human_review) {
    return "review";
  }
  return "blocked";
}

function verdictLabel(decision = {}) {
  const value = String(decision.verdict_class || "review_required").replace(/_/g, " ");
  return value.replace(/\b\w/g, (char) => char.toUpperCase());
}

function compactList(items = [], limit = 3) {
  const visible = (items || []).slice(0, limit);
  const rest = Math.max((items || []).length - visible.length, 0);
  return [
    ...visible.map((item) => `<li>${escapeHtml(String(item))}</li>`),
    rest ? `<li>+${escapeHtml(String(rest))} more in packet</li>` : "",
  ].join("");
}

function movementLane(label, items = [], tone = "review") {
  const values = (items || []).filter(Boolean);
  return `
    <div class="repo-movement-lane ${tone}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(values.length ? values.join(", ") : "none")}</strong>
    </div>
  `;
}

function proofItemsForPacket(packet) {
  const items = packet?.review_run?.missing_proof;
  if (!Array.isArray(items) || !items.length) return DEFAULT_REVIEW_PROOF_ITEMS;
  return items
    .map((item) => ({
      id: String(item?.id || "").trim(),
      label: String(item?.label || item?.id || "").trim(),
    }))
    .filter((item) => item.id && item.label);
}

function attachedProofIds(packet) {
  const attached = packet?.proof_resolution?.attached_proof || packet?.review_run?.attached_proof || [];
  return new Set((attached || []).map((item) => String(item?.id || "").trim()).filter(Boolean));
}

function reviewDeltaRows(packet) {
  const delta = packet?.review_delta || {};
  if (!delta.packet_changed) return [];
  const proofLabels = (delta.new_proof || [])
    .map((item) => item?.label || item?.id)
    .filter(Boolean)
    .join(" + ");
  return [
    ["Same request", delta.same_request ? "true" : "false"],
    ["New proof", proofLabels || "attached"],
    ["Packet", `${delta.packet_revision_before || "rev_1"} -> ${delta.packet_revision_after || "rev_2"}`],
    ["Portkey", `${delta.portkey_before || "Block"} -> ${delta.portkey_after || "Allow with policy"}`],
    ["Still blocked", (delta.still_blocked || []).join(", ") || "none"],
  ];
}

function updateProofAttachButton() {
  if (!repoProofResolutionCard) return;
  const button = repoProofResolutionCard.querySelector(".repo-proof-attach-action");
  const checked = Array.from(repoProofResolutionCard.querySelectorAll('input[type="checkbox"]')).filter(
    (input) => input.checked && !input.disabled
  );
  if (button) button.disabled = checked.length === 0;
}

function renderRepoProofResolution(packet) {
  if (!repoProofResolutionCard) return;
  const proof = packet.proof_resolution || {};
  const readyForRerun = Boolean(proof.ready_for_rerun || packet?.review_run?.packet?.ready_for_rerun);
  const rerunComplete = packet?.review_run?.stage === "ready_to_export" || Boolean(packet?.review_delta?.packet_changed);
  const attachedIds = attachedProofIds(packet);
  const proofItems = proofItemsForPacket(packet);
  const deltaRows = reviewDeltaRows(packet);
  const checklist = repoProofResolutionCard.querySelector(".repo-proof-checklist");
  const button = repoProofResolutionCard.querySelector(".repo-proof-attach-action");
  const status = repoProofResolutionCard.querySelector(".repo-proof-attach-status");
  const delta = repoProofResolutionCard.querySelector(".repo-review-delta");
  repoProofResolutionCard.dataset.readyForRerun = String(readyForRerun);
  repoProofResolutionCard.dataset.rerunComplete = String(rerunComplete);

  const title = repoProofResolutionCard.querySelector("h3");
  if (title) {
    title.textContent = rerunComplete
      ? "Updated packet generated."
      : readyForRerun
        ? "Proof attached. Rerun required."
        : "Attach proof before rerun.";
  }
  if (checklist) {
    checklist.innerHTML = proofItems
      .map((item) => {
        const checked = attachedIds.has(item.id);
        return `
          <label class="repo-proof-check${checked ? " attached" : ""}">
            <input type="checkbox" data-proof-id="${escapeHtml(item.id)}" data-proof-label="${escapeHtml(item.label)}"${checked ? " checked" : ""}${readyForRerun || rerunComplete ? " disabled" : ""} />
            <span>${escapeHtml(item.label)}</span>
          </label>
        `;
      })
      .join("");
    checklist.querySelectorAll('input[type="checkbox"]').forEach((input) => {
      input.addEventListener("change", updateProofAttachButton);
    });
  }
  if (button) {
    button.disabled = rerunComplete || (!readyForRerun && !Array.from(repoProofResolutionCard.querySelectorAll('input[type="checkbox"]')).some((input) => input.checked && !input.disabled));
    button.textContent = rerunComplete ? "Packet regenerated" : readyForRerun ? "Regenerate packet" : "Attach checked proof";
    button.onclick = rerunComplete ? null : readyForRerun ? () => rerunReviewRunPacket() : () => attachReviewRunProof();
  }
  if (delta) {
    if (deltaRows.length) {
      delta.hidden = false;
      delta.innerHTML = deltaRows
        .map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>`)
        .join("");
    } else {
      delta.hidden = true;
      delta.innerHTML = "";
    }
  }
  if (status) {
    status.classList.remove("error");
    status.textContent = rerunComplete
      ? "Same request. New proof changed packet state; Portkey can allow with policy."
      : readyForRerun
      ? "Proof attached. Verdict unchanged; regenerate the packet before movement changes."
      : "No proof attached. Verdict unchanged.";
  }
}

function setRepoCockpitBusy(loading) {
  if (btnRunRepoProof) {
    btnRunRepoProof.dataset.loading = String(loading);
    btnRunRepoProof.disabled = loading || !isReviewRepoReady();
    btnRunRepoProof.textContent = loading ? "Reviewing access..." : "Review access";
  }
  if (repoCockpitStatus) {
    repoCockpitStatus.classList.remove("error");
    if (loading) {
      repoCockpitStatus.textContent = "Collecting proof and building the IA Packet...";
    } else if (repoProofCockpit?.dataset.loaded !== "true") {
      repoCockpitStatus.textContent = isReviewRepoReady()
        ? "Repo connected and indexed. Ready to generate the packet."
        : "Connect and index one repo before generating a packet.";
    }
  }
  if (repoCoachRead) {
    repoCoachRead.textContent =
      "Current read: packet generated from the selected ReviewRun. Movement stays scoped until missing proof is attached and review is rerun.";
  }
  if (packetCoachStatus) {
    packetCoachStatus.hidden = false;
    packetCoachStatus.textContent =
      "Packet ready. Ask IA for current read, blockers, next human action, downstream impact, or safety.";
  }
}

async function fetchPortkeyProofForFixture(fixtureId) {
  const [previewRes, proofRes] = await Promise.all([
    fetch(packetPortkeyPreviewPath(fixtureId)),
    fetch(packetPortkeyProofLoopPath(fixtureId)),
  ]);
  const previewData = await previewRes.json().catch(() => ({}));
  const proofData = await proofRes.json().catch(() => ({}));
  if (!previewRes.ok) throw new Error(previewData.detail || "Portkey gate preview failed");
  if (!proofRes.ok) throw new Error(proofData.detail || "Portkey proof loop failed");
  return {
    payload: previewData.portkey || previewData,
    proofLoop: proofData.portkey_guardrail_proof_loop || proofData,
  };
}

async function fetchRepoSponsorTrace() {
  const res = await fetch("/api/walkthrough");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Sponsor proof trace failed");
  return data.sponsor_proof_trace || null;
}

function renderRepoProofCockpit(packet, portkeyPayload, portkeyProofLoop) {
  if (!repoProofCockpit) return;
  const decision = packet.decision || {};
  const trace = packet.sponsor_proof_trace || {};
  const packetRef = packet.packet_reference || {};
  const guardrail = portkeyPayload?.portkey_guardrail_response || {};
  const policy = portkeyPayload?.usage_policy_plan?.request_body || {};
  const proofCall = portkeyProofLoop?.portkey_call || {};
  const tone = verdictTone(decision);
  const movement = packet.movement_classes || {};
  const delta = packet.review_delta || {};
  const sourceTruth = packetRef.source_of_truth || "ReviewRun";

  repoProofCockpit.dataset.loaded = "true";
  if (repoProofResult) {
    repoProofResult.hidden = false;
  }
  if (repoCockpitVerdict) {
    repoCockpitVerdict.className = `repo-verdict-card ${tone}`;
    repoCockpitVerdict.innerHTML = `
      <span>IA verdict</span>
      <strong>${escapeHtml(verdictLabel(decision))}</strong>
    `;
  }
  if (repoCockpitStatus) {
    repoCockpitStatus.classList.remove("error");
    const repoName = currentReviewRun?.selected_repo?.full_name || selectedReviewRepo()?.full_name || "selected repo";
    repoCockpitStatus.textContent = delta.packet_changed
      ? `Packet ${delta.packet_revision_before || "rev_1"} -> ${delta.packet_revision_after || packetRef.revision_id}. Same request; attached proof changed packet state.`
      : `Packet ${packetRef.revision_id || "rev_1"} is tied to ${repoName}. Decision lock unchanged; downstream writes remain false.`;
  }
  if (btnExportRepoBrief) {
    btnExportRepoBrief.disabled = !packet.copy_review_brief;
  }
  renderRepoProofResolution(packet);

  if (repoNextActionCard) {
    repoNextActionCard.innerHTML = `
      <span class="repo-card-label">Next human action</span>
      <h3>${escapeHtml(decision.next_human_action || "Human review required before access moves.")}</h3>
      <p>${escapeHtml(sourceTruth)} ${escapeHtml(currentReviewRun?.run_id || packetRef.run_id || "local")} generated a compact packet for ${escapeHtml(currentReviewRun?.selected_repo?.full_name || selectedReviewRepo()?.full_name || "the selected repo")}.</p>
      <div class="repo-movement-grid" aria-label="Packet movement classes">
        ${movementLane("Allowed", movement.allowed || packet.allowed || [], "allowed")}
        ${movementLane("Review required", movement.review_required || packet.review_required || [], "review")}
        ${movementLane("Blocked", movement.blocked || packet.blocked || [], "blocked")}
      </div>
      <div class="repo-outcome-grid">
        <div class="repo-outcome ${decision.production_access ? "approved" : "blocked"}">
          <span>Production</span><strong>${escapeHtml(String(decision.production_access))}</strong>
        </div>
        <div class="repo-outcome ${decision.permission_grants ? "approved" : "blocked"}">
          <span>Grants</span><strong>${escapeHtml(String(decision.permission_grants))}</strong>
        </div>
        <div class="repo-outcome ${decision.external_writes ? "approved" : "blocked"}">
          <span>Writes</span><strong>${escapeHtml(String(decision.external_writes))}</strong>
        </div>
      </div>
      <details class="repo-proof-details">
        <summary>Why IA held the line</summary>
        <ul>${compactList(packet.missing_proof || [], 3)}</ul>
      </details>
    `;
  }

  if (repoSponsorProofCard) {
    repoSponsorProofCard.innerHTML = `
      <summary>
        <span class="repo-card-label">ProofGraph</span>
        <strong>${escapeHtml(String(trace.step_count || 0))} proof steps mapped</strong>
      </summary>
      <div class="repo-accordion-body">
        <p>${escapeHtml((trace.sponsor_order || ["Tavily", "Composio", "OpenClaw", "Nebius"]).join(" -> "))}</p>
        <div class="repo-outcome-grid">
          <div class="repo-outcome approved"><span>Decision lock</span><strong>${escapeHtml(String(trace.decision_lock_unchanged ?? true))}</strong></div>
          <div class="repo-outcome ${trace.all_non_executing === false ? "blocked" : "approved"}"><span>Writes</span><strong>${escapeHtml(String(trace.all_non_executing === false))}</strong></div>
          <div class="repo-outcome review"><span>Live keys</span><strong>${escapeHtml(String((trace.steps || []).some((step) => step.used_live_key)))}</strong></div>
        </div>
        <p class="repo-microcopy">Generated from the ReviewRun. Sponsors contribute proof only. IA keeps the packet authority locked.</p>
        <a class="btn-ghost repo-secondary-link" href="/proofgraph?fixture=support_triage_agent">Open ProofGraph</a>
      </div>
    `;
    repoSponsorProofCard.open = false;
  }

  if (repoPortkeyCard) {
    repoPortkeyCard.innerHTML = `
      <summary>
        <span class="repo-card-label">Portkey</span>
        <strong>${guardrail.verdict ? "Would allow" : "Would block"} this movement</strong>
      </summary>
      <div class="repo-accordion-body">
        <p>Webhook ${escapeHtml(proofCall.path || "/api/portkey/guardrail")} returns the IA packet verdict before model or spend movement.</p>
        <div class="repo-outcome-grid">
          <div class="repo-outcome ${guardrail.verdict ? "approved" : "blocked"}"><span>Verdict</span><strong>${escapeHtml(String(guardrail.verdict ?? false))}</strong></div>
          <div class="repo-outcome blocked"><span>Credit limit</span><strong>${escapeHtml(String(policy.credit_limit ?? 0))}</strong></div>
          <div class="repo-outcome approved"><span>API mutation</span><strong>false</strong></div>
        </div>
        <code class="repo-packet-ref">${escapeHtml(packetRef.packet_id || "")}</code>
      </div>
    `;
    repoPortkeyCard.open = false;
  }
}

async function attachReviewRunProof() {
  if (!currentReviewRun?.run_id || !repoProofResolutionCard) return;
  const status = repoProofResolutionCard.querySelector(".repo-proof-attach-status");
  const button = repoProofResolutionCard.querySelector(".repo-proof-attach-action");
  const selected = Array.from(repoProofResolutionCard.querySelectorAll('input[type="checkbox"]'))
    .filter((input) => input.checked && !input.disabled)
    .map((input) => ({
      id: input.dataset.proofId,
      label: input.dataset.proofLabel,
      evidence_note: "Human checked this proof item in the ReviewRun cockpit.",
    }));

  if (!selected.length) {
    if (status) {
      status.textContent = "Select at least one proof item to attach.";
      status.classList.add("error");
    }
    return;
  }

  if (button) {
    button.disabled = true;
    button.textContent = "Attaching proof...";
  }
  if (status) {
    status.classList.remove("error");
    status.textContent = "Attaching proof without changing verdict...";
  }
  try {
    const res = await fetch(`/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/proof`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ proof_items: selected }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.detail || "Proof attachment failed");
    currentReviewRun = data.run || currentReviewRun;
    const nextPacket = {
      ...(data.packet || {}),
      sponsor_proof_trace: packetDetail?.sponsor_proof_trace,
    };
    packetDetail = nextPacket;
    renderRepoProofCockpit(nextPacket, packetPortkeyPreview, packetPortkeyProofLoop);
    if (repoCockpitStatus) {
      repoCockpitStatus.classList.remove("error");
      repoCockpitStatus.textContent =
        "Proof attached. Verdict and Portkey state unchanged; regenerate the packet before movement changes.";
    }
    if (repoCoachRead) {
      repoCoachRead.textContent =
        "Current read: proof is attached to the ReviewRun. IA still needs a rerun before the packet or Portkey state can change.";
    }
  } catch (err) {
    if (status) {
      status.textContent = String(err.message || err);
      status.classList.add("error");
    }
    if (button) {
      button.disabled = false;
      button.textContent = "Attach checked proof";
    }
  }
}

async function rerunReviewRunPacket() {
  if (!currentReviewRun?.run_id || !repoProofResolutionCard) return;
  const status = repoProofResolutionCard.querySelector(".repo-proof-attach-status");
  const button = repoProofResolutionCard.querySelector(".repo-proof-attach-action");
  if (button) {
    button.disabled = true;
    button.textContent = "Regenerating packet...";
  }
  if (status) {
    status.classList.remove("error");
    status.textContent = "Regenerating from the same request and attached proof...";
  }
  try {
    const res = await fetch(`/api/review-runs/${encodeURIComponent(currentReviewRun.run_id)}/rerun`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_request: DEFAULT_REVIEW_ACCESS_REQUEST }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.detail || "ReviewRun rerun failed");
    currentReviewRun = data.run || currentReviewRun;
    packetPortkeyPreview = data.portkey || packetPortkeyPreview;
    const nextPacket = {
      ...(data.packet || {}),
      sponsor_proof_trace: packetDetail?.sponsor_proof_trace,
    };
    packetDetail = nextPacket;
    renderRepoProofCockpit(nextPacket, packetPortkeyPreview, packetPortkeyProofLoop);
    if (repoCockpitStatus) {
      repoCockpitStatus.classList.remove("error");
      repoCockpitStatus.textContent =
        "Updated packet generated. Same request; new proof changed packet state; Portkey reads the new revision.";
    }
    if (repoCoachRead) {
      repoCoachRead.textContent =
        "Current read: proof changed the packet state. Portkey can allow scoped movement under policy while admin, org-wide write, and secrets stay blocked.";
    }
  } catch (err) {
    if (status) {
      status.textContent = String(err.message || err);
      status.classList.add("error");
    }
    if (button) {
      button.disabled = false;
      button.textContent = "Regenerate packet";
    }
  }
}

async function runRepoProofCockpit() {
  if (!isReviewRepoReady()) {
    if (repoCockpitStatus) {
      repoCockpitStatus.textContent = "Connect and index one GitHub repo before generating a packet.";
      repoCockpitStatus.classList.add("error");
    }
    return;
  }
  setRepoCockpitBusy(true);
  try {
    const fixtureId = REPO_PROOF_FIXTURE;
    const runId = currentReviewRun?.run_id;
    const packetRes = await fetch(`/api/review-runs/${encodeURIComponent(runId)}/packet`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_request: DEFAULT_REVIEW_ACCESS_REQUEST }),
    });
    const packetData = await packetRes.json().catch(() => ({}));
    if (!packetRes.ok || !packetData.ok) throw new Error(packetData.detail || "ReviewRun packet generation failed");
    currentReviewRun = packetData.run || currentReviewRun;
    const packet = packetData.packet || {};
    const [{ payload, proofLoop }, sponsorTrace] = await Promise.all([
      fetchPortkeyProofForFixture(fixtureId),
      fetchRepoSponsorTrace().catch(() => packet.sponsor_proof_trace || null),
    ]);
    const cockpitPacket = {
      ...packet,
      sponsor_proof_trace: sponsorTrace || packet.sponsor_proof_trace,
    };
    packetDetail = cockpitPacket;
    packetPortkeyPreview = payload;
    packetPortkeyProofLoop = proofLoop;
    renderRepoProofCockpit(cockpitPacket, payload, proofLoop);
  } catch (err) {
    if (repoCockpitStatus) {
      repoCockpitStatus.textContent = String(err.message || err);
      repoCockpitStatus.classList.add("error");
    }
  } finally {
    setRepoCockpitBusy(false);
    updateReviewCtaState();
  }
}

async function copyRepoBrief() {
  if (!packetDetail?.copy_review_brief) {
    await runRepoProofCockpit();
  }
  const text = packetDetail?.copy_review_brief || "";
  if (!text) {
    if (repoCockpitStatus) {
      repoCockpitStatus.textContent = "Review brief unavailable.";
      repoCockpitStatus.classList.add("error");
    }
    return;
  }
  const copied = await copyTextWithFallback(text);
  if (repoCockpitStatus) {
    repoCockpitStatus.classList.toggle("error", !copied);
    repoCockpitStatus.textContent = copied
      ? "Review brief copied. Packet authority unchanged."
      : "Clipboard unavailable. Inspect packet to export.";
  }
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

function renderPacketTeamLenses(teamLenses) {
  const wrap = document.createElement("div");
  wrap.className = "team-lens-list";
  const lenses = teamLenses?.lenses || [];
  lenses.forEach((lens) => {
    const row = document.createElement("article");
    row.className = `team-lens-row ${lens.relevance === "direct" ? "direct" : "context"}`;
    const missingCount = (lens.missing_proof || []).length;
    const blockedCount = (lens.blocked_claims || []).length;
    row.innerHTML = `
      <div class="team-lens-head">
        <strong>${escapeHtml(lens.label || "Team")}</strong>
        <span>${escapeHtml(lens.relevance || "context")}</span>
      </div>
      <p>${escapeHtml(lens.review_focus || "")}</p>
      <code>${escapeHtml(lens.next_validation || "Review packet state before scope moves.")}</code>
      <div class="team-lens-meta">
        <span>owner: ${escapeHtml(lens.reviewer_owner || "Named human reviewer")}</span>
        <span>blocked ${escapeHtml(String(blockedCount))} · proof ${escapeHtml(String(missingCount))}</span>
      </div>
      <small>${escapeHtml(lens.safety_note || "This lens reads the IA Packet only.")}</small>
    `;
    wrap.appendChild(row);
  });
  if (!lenses.length) {
    const empty = document.createElement("p");
    empty.className = "walkthrough-summary";
    empty.textContent = "No team lenses are attached to this packet projection yet.";
    wrap.appendChild(empty);
  }
  return wrap;
}

function renderPacketPortkeyGateCard(payload = null, proofLoop = null) {
  const card = document.createElement("div");
  card.className = "packet-consumer";
  card.id = "packet-portkey-gate-card";
  const proofTruth = proofLoop?.packet_truth || {};
  const proofCall = proofLoop?.portkey_call || {};
  const proofInvariants = proofLoop?.invariants || {};

  if (!payload) {
    card.innerHTML = `
      <span class="trace-subhead">downstream proof loop</span>
      <h4>Portkey asks IA before movement</h4>
      <p>Show the packet-backed webhook verdict, packet reference, latency, and dry-run policy preview.</p>
      <p class="safety-anchor">Read-only. Portkey API call made: false. Policy mutation: false.</p>
    `;
  } else {
    const guardrail = payload.portkey_guardrail_response || {};
    const policy = payload.usage_policy_plan?.request_body || {};
    const packet = payload.ia_packet_reference || {};
    card.innerHTML = `
      <span class="trace-subhead">downstream proof loop</span>
      <h4>Portkey asks IA before movement</h4>
      <p>Webhook verdict: ${escapeHtml(String(proofTruth.verdict ?? guardrail.verdict))}; server latency: ${escapeHtml(String(proofCall.server_elapsed_ms ?? "preview"))}ms; usage credit limit: ${escapeHtml(String(policy.credit_limit ?? 0))}.</p>
      <code class="walkthrough-fact">${escapeHtml(packet.packet_id || "")}</code>
      <div class="portkey-proof-metrics">
        <div><span>Auth required</span><strong>${escapeHtml(String(proofInvariants.auth_required ?? true))}</strong></div>
        <div><span>API call</span><strong>${escapeHtml(String(proofInvariants.portkey_api_call_made ?? payload.api_call_made))}</strong></div>
        <div><span>Policy mutation</span><strong>${escapeHtml(String(proofInvariants.portkey_policy_mutation_allowed ?? false))}</strong></div>
        <div><span>Packet authority</span><strong>${escapeHtml(String(proofInvariants.packet_remains_authority ?? true))}</strong></div>
      </div>
      <p class="safety-anchor">Portkey receives a packet-backed verdict. IA does not push policy, mutate Portkey, or trust raw agent intent.</p>
    `;
  }

  const actions = document.createElement("div");
  actions.className = "walk-actions";
  const preview = document.createElement("button");
  preview.type = "button";
  preview.className = payload ? "btn-ghost" : "btn-primary";
  preview.textContent = payload ? "Refresh proof loop" : "Show Portkey proof loop";
  preview.addEventListener("click", () => previewPacketPortkeyGate());
  const exportGate = document.createElement("button");
  exportGate.type = "button";
  exportGate.className = "btn-ghost";
  exportGate.textContent = "Export Portkey gate";
  exportGate.addEventListener("click", () => exportPacketPortkeyGate());
  actions.append(preview, exportGate);
  card.appendChild(actions);
  return card;
}

function updatePacketPortkeyGateCard(payload) {
  const existing = document.getElementById("packet-portkey-gate-card");
  if (!existing) return;
  existing.replaceWith(renderPacketPortkeyGateCard(payload, packetPortkeyProofLoop));
}

function renderPacketDetail(data) {
  packetDetail = data;
  packetPortkeyPreview = null;
  packetPortkeyProofLoop = null;
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
  markPacketReviewRailLoaded();

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
    ${
      trace
        ? `<code class="walkthrough-fact">trace ${escapeHtml(trace.trace_id || "sponsor-proof-trace")}</code>
           <code class="walkthrough-fact">packet ${escapeHtml(trace.packet_id || packet.packet_id || "")}</code>
           <div class="trace-metrics compact">
             <div><span>Decision lock</span><strong>${escapeHtml(String(trace.decision_lock_unchanged))}</strong></div>
             <div><span>Fallback</span><strong>${escapeHtml(String(trace.all_fallback_used))}</strong></div>
             <div><span>Live keys</span><strong>${escapeHtml(String((trace.steps || []).some((step) => step.used_live_key)))}</strong></div>
             <div><span>Writes</span><strong>${escapeHtml(String(!trace.all_non_executing))}</strong></div>
           </div>`
        : ""
    }
    <p class="safety-anchor">Sponsors collect proof only; approve ${escapeHtml(String(trace?.approves_access ?? false))} · spend ${escapeHtml(String(trace?.approves_spend ?? false))} · provider ${escapeHtml(String(trace?.selects_provider ?? false))}</p>
  `;
  const packetBlastGraph = renderBlastRadiusGraph({ trace, run: null, context: "packet" });
  if (packetBlastGraph) packetSponsorCard.appendChild(packetBlastGraph);
  const proofGraphActions = document.createElement("div");
  proofGraphActions.className = "walk-actions proofgraph-actions";
  proofGraphActions.innerHTML = `
    <a class="btn-primary" href="${proofGraphUrl()}">Open ProofGraph</a>
    <span class="walkthrough-summary">Shows the full packet authority map: sponsors -> IA Packet -> downstream systems.</span>
  `;
  packetSponsorCard.appendChild(proofGraphActions);

  packetDownstreamCard.innerHTML = `
    <span class="eyebrow">Downstream trust</span>
    <h3>${escapeHtml(String((data.downstream_consumers || []).length))} consumer patterns read the same packet</h3>
    <p class="walkthrough-summary">Gateways, CI, spend controls, review queues, and observability read the packet reference. Portkey can ask IA for a packet-backed verdict before model or spend movement.</p>
  `;
  packetDownstreamCard.appendChild(renderPacketConsumers(data.downstream_consumers || []));
  packetDownstreamCard.appendChild(renderPacketPortkeyGateCard(null, null));

  packetTeamCard.innerHTML = `
    <span class="eyebrow">Cross-functional review</span>
    <h3>Teams reading this packet</h3>
    <p class="walkthrough-summary">Every lens reads the same packet reference. Teams get different review focus; none can approve, assign, dispatch, grant, write, or mutate.</p>
  `;
  packetTeamCard.appendChild(renderPacketTeamLenses(data.team_lenses));

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
  btnExportPortkeyGate.disabled = !fixture.fixture_id;
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
    unlockPacketCoach();
    setPacketInlineCoachStatus("Ask a packet-backed follow-up. IA stays read-only and cannot approve or write.");
    window.history.replaceState({}, "", packetDetailUrl(data.fixture?.fixture_id || fixtureId));
    try {
      await loadPacketPortkeyPreview();
      setPacketToast("IA Packet loaded. Portkey proof loop ready.");
    } catch (_) {
      setPacketToast("IA Packet loaded. Portkey proof loop can be previewed next.");
    }
  } catch (err) {
    setPacketToast(String(err.message || err), true);
  } finally {
    btnLoadPacket.disabled = false;
  }
}

async function askPacketInlineCoach(prompt) {
  if (packetInlineCoachBusy) return;
  const message = String(prompt || "").trim();
  if (!message) return;

  setPacketInlineCoachBusy(true);
  setPacketInlineCoachStatus("Answering from the IA Packet...");
  if (packetInlineCoachOutput) {
    packetInlineCoachOutput.innerHTML = "";
    const pending = document.createElement("div");
    pending.className = "packet-inline-coach-pending";
    pending.textContent = "Building packet-backed answer...";
    packetInlineCoachOutput.appendChild(pending);
  }

  try {
    if (!packetDetail) {
      await loadPacketDetail();
    }
    const fixtureId = currentPacketFixtureForChat() || packetSelectedFixtureId();
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        current_fixture: fixtureId,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Ask IA failed (${res.status})`);
    if (data.session_id) {
      sessionId = data.session_id;
      localStorage.setItem(STORAGE_KEY, sessionId);
      chatStorageScope = `chat_${sessionId}`;
    }
    if (!packetInlineCoachOutput) return;
    packetInlineCoachOutput.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "message assistant packet-inline-coach-message";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    renderAssistantMarkdown(bubble, data.reply || "");
    addDownloadButtons(bubble, (data.output_files || []).filter((f) => f.file_id));
    wrap.appendChild(bubble);
    packetInlineCoachOutput.appendChild(wrap);
    setPacketInlineCoachStatus("Packet-backed answer rendered. Decision lock unchanged.");
  } catch (err) {
    if (packetInlineCoachOutput) {
      packetInlineCoachOutput.innerHTML = "";
      const error = document.createElement("p");
      error.className = "packet-inline-coach-error";
      error.textContent = String(err.message || err);
      packetInlineCoachOutput.appendChild(error);
    }
    setPacketInlineCoachStatus("Ask IA could not render this packet answer.", true);
  } finally {
    setPacketInlineCoachBusy(false);
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

async function loadPacketPortkeyPreview() {
  const fixtureId = packetDetail?.fixture?.fixture_id || packetSelectedFixtureId();
  if (!fixtureId) {
    throw new Error("Load an IA Packet first.");
  }
  const { payload, proofLoop } = await fetchPortkeyProofForFixture(fixtureId);
  packetPortkeyProofLoop = proofLoop;
  packetPortkeyPreview = payload;
  updatePacketPortkeyGateCard(payload, packetPortkeyProofLoop);
  return payload;
}

async function previewPacketPortkeyGate() {
  try {
    setPacketToast("Loading Portkey proof loop...");
    await loadPacketPortkeyPreview();
    setPacketToast("Portkey proof loop ready. No API call made.");
  } catch (err) {
    setPacketToast(String(err.message || err), true);
  }
}

async function exportPacketPortkeyGate() {
  try {
    setPacketToast("Exporting Portkey dry-run gate...");
    const payload = packetPortkeyPreview || await loadPacketPortkeyPreview();
    downloadJsonPayload(payload, packetPortkeyExportName(payload));
    setPacketToast("Portkey dry-run gate JSON exported. No API call made.");
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

function formatSponsorName(value) {
  const names = {
    tavily: "Tavily",
    composio: "Composio",
    openclaw: "OpenClaw",
    nebius: "Nebius",
  };
  return names[value] || formatSubscriberName(value);
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

function sponsorStepState({ live = false, dryRun = false, fallback = false, locked = false }) {
  if (locked) return "locked";
  if (live && !fallback) return "live";
  if (dryRun) return "dry-run";
  if (fallback) return "fallback";
  return "planned";
}

function renderSponsorProofStep({ label, role, state, detail, meta }) {
  const row = document.createElement("div");
  row.className = `sponsor-proof-step ${state}`;
  row.innerHTML = `
    <span class="proof-step-state">${escapeHtml(state)}</span>
    <strong>${escapeHtml(label)}</strong>
    <em>${escapeHtml(role)}</em>
    <p>${escapeHtml(detail)}</p>
    <code>${escapeHtml(meta)}</code>
  `;
  return row;
}

function renderSponsorProofLoop({ trace, run, tavily, composio, nebius, synthesis, portkey }) {
  const openclawStep = (run?.collector_steps || trace?.steps || []).find(
    (step) => step.sponsor === "openclaw"
  );
  const tavilyCandidates = Array.isArray(tavily?.evidence_candidates)
    ? tavily.evidence_candidates
    : [];
  const tavilySourceCount = tavilyCandidates.reduce(
    (total, item) => total + (Array.isArray(item.source_urls) ? item.source_urls.length : 0),
    0
  );
  const composioSummary = composio?.permission_diff_summary || {};
  const sourceIndexCount = Number(synthesis?.source_index_count || 0);
  const citedIds = Array.isArray(synthesis?.synthesis?.cited_source_ids)
    ? synthesis.synthesis.cited_source_ids
    : [];

  const loop = document.createElement("div");
  loop.className = "sponsor-proof-loop";
  const steps = [
    {
      label: "Tavily",
      role: "source candidates",
      state: sponsorStepState({
        live: Boolean(tavily?.live_call_attempted),
        fallback: Boolean(tavily?.fallback_used),
      }),
      detail: tavily
        ? `${tavily.live_call_count || 0} live calls, ${tavilySourceCount} source URLs collected.`
        : "Plans source searches for missing proof without reducing proof debt.",
      meta: tavily
        ? `fallback ${String(tavily.fallback_used)}`
        : "read-only evidence",
    },
    {
      label: "Nebius",
      role: "reviewer synthesis",
      state: sponsorStepState({
        live: Boolean(synthesis?.live_call_attempted || nebius?.live_call_attempted),
        fallback: Boolean(synthesis?.fallback_used ?? nebius?.fallback_used),
      }),
      detail: synthesis
        ? `${sourceIndexCount} Tavily sources indexed; cited ${citedIds.length || 0} source IDs.`
        : "Narrates locked packet fields and source candidates for human review.",
      meta: synthesis
        ? `synthesis ${synthesis.status || "pending"}`
        : "locked-field narration",
    },
    {
      label: "Composio",
      role: "permission diff",
      state: sponsorStepState({ dryRun: true, fallback: Boolean(composio?.fallback_used) }),
      detail: composio
        ? `${composioSummary.tool_count || 0} tool plans; ${composioSummary.blocked_write_count || 0} writes blocked.`
        : "Builds a dry-run permission diff; execute remains blocked.",
      meta: composio
        ? `api_call_made ${String(composio.api_call_made)}`
        : "dry-run only",
    },
    {
      label: "OpenClaw",
      role: "runtime trace",
      state: sponsorStepState({ fallback: Boolean(openclawStep?.fallback_used) }),
      detail: openclawStep?.output_summary || "Records the runtime trace shape for blocked/dry-run steps.",
      meta: `would_execute ${String(openclawStep?.would_execute ?? false)}`,
    },
    {
      label: "Portkey",
      role: "downstream gate",
      state: sponsorStepState({ dryRun: true }),
      detail: portkey
        ? `Dry-run guardrail verdict ${String(portkey.portkey_guardrail_response?.verdict)}; credit limit ${String(portkey.usage_policy_plan?.request_body?.credit_limit ?? 0)}.`
        : "Previews the downstream gate policy without a Portkey API mutation.",
      meta: `api_call_made ${String(portkey?.api_call_made ?? false)}`,
    },
    {
      label: "IA Packet",
      role: "authority lock",
      state: sponsorStepState({ locked: true }),
      detail: "Decision, proof debt, and safety state stay unchanged after sponsor proof collection.",
      meta: `decision_lock ${String(run?.invariants?.decision_lock_unchanged ?? trace?.decision_lock_unchanged ?? true)}`,
    },
  ];
  steps.forEach((step, index) => {
    loop.appendChild(renderSponsorProofStep({ ...step, label: `${index + 1}. ${step.label}` }));
  });
  return loop;
}

function renderSponsorSourcePanel({ synthesis, tavily }) {
  if (!synthesis && !tavily) return null;
  const panel = document.createElement("div");
  panel.className = "sponsor-source-panel";
  const citedIds = Array.isArray(synthesis?.synthesis?.cited_source_ids)
    ? synthesis.synthesis.cited_source_ids
    : [];
  const sourceIndex = Array.isArray(synthesis?.source_index) ? synthesis.source_index : [];
  const topSources = sourceIndex.slice(0, 3);
  const summary =
    synthesis?.synthesis?.reviewer_summary ||
    "Tavily source candidates are available for human review; IA does not approve from sources alone.";
  panel.innerHTML = `
    <div class="sponsor-source-head">
      <span class="trace-subhead">Live source synthesis</span>
      <strong>${escapeHtml(synthesis?.status || "source candidates collected")}</strong>
      <code>cited ${escapeHtml(citedIds.join(", ") || "none")} · no new URLs ${escapeHtml(String(synthesis?.invariants?.no_new_urls ?? true))}</code>
    </div>
    <p class="walkthrough-summary">${escapeHtml(summary)}</p>
  `;
  if (topSources.length) {
    const links = document.createElement("div");
    links.className = "sponsor-source-links";
    topSources.forEach((source) => {
      const url = String(source.url || "");
      const safeUrl = url.startsWith("http://") || url.startsWith("https://") ? url : "";
      const item = document.createElement(safeUrl ? "a" : "span");
      item.className = "sponsor-source-link";
      if (safeUrl) {
        item.href = safeUrl;
        item.target = "_blank";
        item.rel = "noreferrer";
      }
      item.innerHTML = `
        <code>${escapeHtml(source.source_id || "tavily")}</code>
        <span>${escapeHtml(source.title || source.query || "Tavily source candidate")}</span>
      `;
      links.appendChild(item);
    });
    panel.appendChild(links);
  }
  const invariants = document.createElement("div");
  invariants.className = "sponsor-source-locks";
  [
    ["Tavily only", synthesis?.invariants?.source_ids_from_tavily_only ?? true],
    ["No new URLs", synthesis?.invariants?.no_new_urls ?? true],
    ["Can approve", synthesis?.invariants?.can_approve_access ?? false],
    ["Can reduce proof debt", synthesis?.invariants?.can_reduce_proof_debt ?? false],
  ].forEach(([label, value]) => {
    const item = document.createElement("div");
    item.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong>`;
    invariants.appendChild(item);
  });
  panel.appendChild(invariants);
  return panel;
}

function riskTone(level) {
  const normalized = String(level || "review").toLowerCase();
  if (normalized === "critical") return "critical";
  if (normalized === "high") return "high";
  if (normalized === "medium") return "medium";
  return "low";
}

function blastRadiusFrom({ trace, run }) {
  return run?.blast_radius || trace?.blast_radius || null;
}

function renderBlastRadiusGraph({ trace, run, context = "walkthrough" }) {
  const blastRadius = blastRadiusFrom({ trace, run });
  if (!blastRadius) return null;

  const summary = blastRadius.summary || run?.live_proof_intelligence?.blast_radius || {};
  const tools = Array.isArray(blastRadius.tools) ? blastRadius.tools : [];
  const maxRisk = summary.max_risk_level || "review";
  const blockedCount = Number(summary.blocked_action_count || 0);
  const writeCount = Number(summary.write_like_action_count || 0);
  const adminCount = Number(summary.admin_like_action_count || 0);
  const highCriticalCount = Number(summary.high_or_critical_action_count || writeCount + adminCount || blockedCount);
  const wouldExecute = Boolean(summary.would_execute);
  const allBlocked = summary.all_write_or_admin_blocked ?? summary.all_blocked_before_execution ?? true;
  const toolNames = tools.map((tool) => tool.tool).filter(Boolean);
  const sponsorOrder = Array.isArray(trace?.sponsor_order) ? trace.sponsor_order : [];
  const graph = document.createElement("section");
  graph.className = `blast-radius-graph-card ${riskTone(maxRisk)} ${context}`;
  graph.setAttribute("aria-label", "IA blast radius graph");
  graph.innerHTML = `
    <div class="blast-radius-head">
      <div>
        <span class="eyebrow">IA Blast Radius Graph</span>
        <h4>IA maps what can move before anything executes</h4>
        <p class="walkthrough-summary">IA created this graph from sponsor proof. Composio contributes permission diffs; OpenClaw contributes blocked-action trace shape; Tavily and Nebius add evidence and reviewer context. The IA Packet remains the authority.</p>
      </div>
      <div class="blast-risk">
        <span>Max risk</span>
        <strong>${escapeHtml(maxRisk)}</strong>
      </div>
    </div>
    <div class="blast-radius-flow">
      <div class="blast-node">
        <span>Requested systems</span>
        <strong>${escapeHtml(toolNames.length ? toolNames.join(" / ") : "packet scope")}</strong>
        <small>${escapeHtml(sponsorOrder.length ? sponsorOrder.map(formatSponsorName).join(" -> ") : "sponsor proof")}</small>
      </div>
      <div class="blast-node hero">
        <span>IA containment map</span>
        <strong>${escapeHtml(String(blockedCount))} blocked actions</strong>
        <small>${escapeHtml(String(writeCount))} write-like · ${escapeHtml(String(adminCount))} admin-like</small>
      </div>
      <div class="blast-node safe">
        <span>Outcome</span>
        <strong>executes ${escapeHtml(String(wouldExecute))}</strong>
        <small>human review ${escapeHtml(String(summary.human_review_required ?? trace?.requires_human_review ?? true))}</small>
      </div>
    </div>
    <div class="blast-bars" aria-label="Blast radius action classes">
      <div>
        <span>High / critical</span>
        <strong>${escapeHtml(String(highCriticalCount))}</strong>
      </div>
      <div>
        <span>Write-like</span>
        <strong>${escapeHtml(String(writeCount))}</strong>
      </div>
      <div>
        <span>Admin-like</span>
        <strong>${escapeHtml(String(adminCount))}</strong>
      </div>
      <div>
        <span>All blocked</span>
        <strong>${escapeHtml(String(allBlocked))}</strong>
      </div>
    </div>
  `;

  if (tools.length) {
    const toolGrid = document.createElement("div");
    toolGrid.className = "blast-tool-grid";
    tools.slice(0, 4).forEach((tool) => {
      const toolSummary = tool.summary || {};
      const row = document.createElement("article");
      row.className = `blast-tool-row ${riskTone(toolSummary.max_risk_level || tool.blocked_actions?.[0]?.risk_level || maxRisk)}`;
      row.innerHTML = `
        <div>
          <strong>${escapeHtml(tool.tool || "tool")}</strong>
          <span>${escapeHtml(tool.blast_radius_class || "review scope")}</span>
        </div>
        <code>${escapeHtml(String(toolSummary.blocked_action_count || 0))} blocked · execute ${escapeHtml(String(toolSummary.would_execute ?? false))}</code>
      `;
      toolGrid.appendChild(row);
    });
    graph.appendChild(toolGrid);
  }

  const authority = document.createElement("p");
  authority.className = "safety-anchor blast-authority";
  authority.textContent = "Sponsors provide signals. IA builds the blast-radius graph, preserves the decision lock, and names the next human review.";
  graph.appendChild(authority);
  return graph;
}

function renderSponsorCard(data) {
  const trace = data.sponsor_proof_trace || {};
  const order = trace.sponsor_order || [];
  const displayOrder = order.map((item) => formatSponsorName(item)).join(" -> ");
  walkthroughSponsorCard.innerHTML = `
    <span class="eyebrow">Sponsor proof trace</span>
    <h3>Live proof loop</h3>
    <p class="walkthrough-summary">One local IA API call orchestrates sponsor proof. ${escapeHtml(displayOrder || "Tavily -> Composio -> OpenClaw -> Nebius")} contribute proof only; the IA Packet stays locked.</p>
  `;
  const run = data.sponsor_proof_run || walkthroughSponsorRun;
  const ledgerRecord = data.sponsor_proof_ledger_record || walkthroughSponsorLedgerRecord;
  const tavily = run?.live_sponsor_proof?.tavily || null;
  const composio = run?.dry_run_sponsor_proof?.composio || null;
  const nebius = run?.live_sponsor_proof?.nebius || null;
  const synthesis = run?.nebius_evidence_synthesis || null;
  const portkey = run?.downstream_previews?.portkey_model_spend_gate || null;
  const safetyForMetrics = run?.safety_boundary || {};
  const metrics = document.createElement("div");
  metrics.className = "trace-metrics";
  const metricRows = run
    ? [
        ["Decision lock", run.invariants?.decision_lock_unchanged],
        ["Live calls", safetyForMetrics.live_calls_made],
        ["Writes", safetyForMetrics.executes_external_writes],
        [
          "Approves",
          Boolean(
            safetyForMetrics.approves_access ||
              safetyForMetrics.approves_spend ||
              safetyForMetrics.grants_permissions
          ),
        ],
      ]
    : [
        ["Decision lock", trace.decision_lock_unchanged],
        ["Fallback", trace.all_fallback_used],
        ["Access evidence", trace.access_evidence_present],
        ["Spend evidence", trace.spend_evidence_present],
      ];
  metricRows.forEach(([label, value]) => {
    const item = document.createElement("div");
    item.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong>`;
    metrics.appendChild(item);
  });
  walkthroughSponsorCard.appendChild(metrics);

  const blastGraph = renderBlastRadiusGraph({ trace, run, context: "walkthrough" });
  if (blastGraph) walkthroughSponsorCard.appendChild(blastGraph);

  walkthroughSponsorCard.appendChild(
    renderSponsorProofLoop({ trace, run, tavily, composio, nebius, synthesis, portkey })
  );

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
  const traceDetails = document.createElement("details");
  traceDetails.className = "trace-detail-toggle";
  traceDetails.innerHTML = "<summary>Raw trace details</summary>";
  traceDetails.appendChild(traceList);

  const traceAction = document.createElement("button");
  traceAction.type = "button";
  traceAction.className = "btn-primary btn-block trace-action";
  traceAction.textContent = "Collect sponsor proof";
  traceAction.setAttribute("aria-label", "Collect non-mutating sponsor proof run");
  traceAction.addEventListener("click", () => collectSponsorProof());
  walkthroughSponsorCard.appendChild(traceAction);

  if (run) {
    const safety = run.safety_boundary || {};
    const tavilyCandidates = Array.isArray(tavily?.evidence_candidates)
      ? tavily.evidence_candidates
      : [];
    const tavilySourceCount = tavilyCandidates.reduce(
      (total, item) => total + (Array.isArray(item.source_urls) ? item.source_urls.length : 0),
      0
    );
    const composioSummary = composio?.permission_diff_summary || {};
    const sponsorRunSummaries = [];
    if (tavily) {
      sponsorRunSummaries.push(
        `Tavily live evidence ${tavily.live_call_attempted ? "attempted" : "not attempted"}; ${tavily.live_call_count || 0} live calls; ${tavilySourceCount} source URLs; fallback ${String(tavily.fallback_used)}.`
      );
    }
    if (composio) {
      sponsorRunSummaries.push(
        `${composioSummary.tool_count || 0} Composio permission diffs generated; ${composioSummary.blocked_write_count || 0} write actions remain blocked; API call made ${String(composio.api_call_made)}.`
      );
    }
    if (nebius) {
      sponsorRunSummaries.push(
        `Nebius reviewer narration ${nebius.live_call_attempted ? "attempted" : "not attempted"}; ${nebius.live_call_count || 0} live calls; fallback ${String(nebius.fallback_used)}; anchors ${String(nebius.required_anchors_present)}.`
      );
    }
    if (synthesis) {
      sponsorRunSummaries.push(
        `Nebius evidence synthesis ${synthesis.live_call_attempted ? "attempted" : "not attempted"}; ${synthesis.live_call_count || 0} live calls; ${synthesis.source_index_count || 0} Tavily sources indexed; fallback ${String(synthesis.fallback_used)}.`
      );
    }
    const runCard = document.createElement("article");
    runCard.className = "sponsor-run-card";
    runCard.innerHTML = `
      <span class="trace-subhead">Latest collected run</span>
      <strong>${escapeHtml(run.run_id || "sponsor proof run")}</strong>
      <code>mode ${escapeHtml(run.mode || "offline_dry_run")} · ledger ${escapeHtml(ledgerRecord?.run_id ? "recorded" : "pending")}</code>
      <div class="trace-metrics compact">
        <div><span>Read only</span><strong>${escapeHtml(String(safety.read_only))}</strong></div>
        <div><span>Live calls</span><strong>${escapeHtml(String(safety.live_calls_made))}</strong></div>
        <div><span>Writes</span><strong>${escapeHtml(String(safety.executes_external_writes))}</strong></div>
        <div><span>Decision lock</span><strong>${escapeHtml(String(run.invariants?.decision_lock_unchanged))}</strong></div>
      </div>
      <p class="walkthrough-summary">${escapeHtml(
        sponsorRunSummaries.length
          ? sponsorRunSummaries.join(" ")
          : "Sponsor proof run collected without changing the packet decision."
      )}</p>
    `;
    walkthroughSponsorCard.appendChild(runCard);
    const sourcePanel = renderSponsorSourcePanel({ synthesis, tavily });
    if (sourcePanel) walkthroughSponsorCard.appendChild(sourcePanel);
  }
  walkthroughSponsorCard.appendChild(traceDetails);

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
  if (walkthroughSponsorRun && !data.sponsor_proof_run) {
    data.sponsor_proof_run = walkthroughSponsorRun;
    data.sponsor_proof_ledger_record = walkthroughSponsorLedgerRecord;
  }
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
  if (!walkthroughPayload?.sponsor_proof_trace) {
    setWalkthroughToast("Sponsor Proof Trace unavailable.", true);
    return;
  }

  btnCollectSponsorProof.disabled = true;
  document.querySelectorAll(".trace-action").forEach((button) => {
    button.disabled = true;
  });
  if (!runtimeHealth) {
    try {
      runtimeHealth = await fetch("/api/health").then((r) => r.json());
    } catch (_) {
      runtimeHealth = null;
    }
  }
  const liveTavily = Boolean(runtimeHealth?.tavily);
  const liveNebius = runtimeHealth?.llm_provider === "nebius";
  setWalkthroughToast(
    liveTavily || liveNebius
      ? `Collecting sponsor proof run with${liveTavily ? " live Tavily evidence" : ""}${liveNebius ? " Nebius narration" : ""}...`
      : "Collecting sponsor proof run..."
  );
  try {
    const res = await fetch("/api/sponsor-proof-runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_path: walkthroughPayload.request_path || "examples/requests/support_triage_trial.yml",
        composio_dry_run: true,
        live_tavily: liveTavily,
        live_nebius: liveNebius,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.detail || "Sponsor proof run failed");
    walkthroughSponsorRun = data.run;
    walkthroughSponsorLedgerRecord = data.ledger_record;
    walkthroughPayload.sponsor_proof_run = data.run;
    walkthroughPayload.sponsor_proof_ledger_record = data.ledger_record;
    renderWalkthrough(walkthroughPayload);
    selectWalkthroughStepById(
      "sponsor_proof_trace",
      `Sponsor proof run ${data.run?.run_id || ""} collected. Decision lock unchanged.`
    );
  } catch (err) {
    setWalkthroughToast(String(err.message || err), true);
  } finally {
    btnCollectSponsorProof.disabled = !walkthroughPayload?.sponsor_proof_trace;
    document.querySelectorAll(".trace-action").forEach((button) => {
      button.disabled = !walkthroughPayload?.sponsor_proof_trace;
    });
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
  const tabs = document.querySelectorAll(".sidebar .tab");
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
      document.body.dataset.activeTab = id || "start";
      const advancedNav = tab.closest(".advanced-nav");
      if (advancedNav) {
        advancedNav.open = true;
      } else {
        document.querySelector(".advanced-nav")?.removeAttribute("open");
      }
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
    runtimeHealth = health;

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

  } catch (_) {
    runtimeHealth = null;
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

packetCoachQuickChips?.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-ask-prompt]");
  if (!btn || busy) return;
  sendMessage(btn.dataset.askPrompt || btn.textContent || "");
});

packetInlineCoachPrompts?.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-ask-prompt]");
  if (!btn) return;
  askPacketInlineCoach(btn.dataset.askPrompt || btn.textContent || "");
});

btnRunRepoProof?.addEventListener("click", () => runRepoProofCockpit());
btnExportRepoBrief?.addEventListener("click", () => copyRepoBrief());
btnReset.addEventListener("click", resetChat);
btnMindInit.addEventListener("click", () => mindInit(false));
btnMindStep.addEventListener("click", mindStep);
btnQueueEvidence.addEventListener("click", queueEvidence);
btnRunRehearsal.addEventListener("click", runSponsorRehearsal);
btnRunUploadedRehearsal.addEventListener("click", runUploadedRehearsal);
btnLoadPacket.addEventListener("click", loadPacketDetail);
btnCopyPacketBrief.addEventListener("click", copyPacketBrief);
btnExportPacket.addEventListener("click", exportPacketResult);
btnExportPortkeyGate.addEventListener("click", exportPacketPortkeyGate);
btnOpenPacketWorkbench.addEventListener("click", () => {
  window.location.href = packetWorkbenchUrl();
});
setupPacketReviewRail();
packetLaneSelect.addEventListener("change", () => {
  renderPacketFixtureOptions();
  packetDetail = null;
  packetPortkeyPreview = null;
  btnCopyPacketBrief.disabled = true;
  btnExportPacket.disabled = true;
  btnExportPortkeyGate.disabled = true;
  setPacketToast("Lane changed. Load an IA Packet to refresh the product object.");
});
packetFixtureSelect.addEventListener("change", () => {
  packetDetail = null;
  packetPortkeyPreview = null;
  btnCopyPacketBrief.disabled = true;
  btnExportPacket.disabled = true;
  btnExportPortkeyGate.disabled = true;
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

document.body.dataset.activeTab = "start";
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
})();
