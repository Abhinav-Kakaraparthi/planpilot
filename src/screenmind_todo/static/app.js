const state = {
  includeNoise: false,
  activityCollapsed: false,
  meetings: [],
  activeMeeting: null,
  dashboard: { tasks: [], activities: [] },
  session: { active: false, mode: "session", label: "Session idle" },
  activeView: "overview",
  copilotMode: "answer",
  floatingMinimized: false,
  floatingPosition: null,
};

const el = {
  navButtons: Array.from(document.querySelectorAll("[data-view-target]")),
  shortcutViewButtons: Array.from(document.querySelectorAll("[data-shortcut-view]")),
  views: Array.from(document.querySelectorAll(".view-panel")),
  watcherStatus: document.querySelector("#watcher-status"),
  heroStatusPill: document.querySelector("#hero-status-pill"),
  watcherToggle: document.querySelector("#watcher-toggle"),
  scanNow: document.querySelector("#scan-now"),
  statOpenTasks: document.querySelector("#stat-open-tasks"),
  statMeetings: document.querySelector("#stat-meetings"),
  statActivities: document.querySelector("#stat-activities"),
  statActivitiesMeta: document.querySelector("#stat-activities-meta"),
  tasks: document.querySelector("#tasks"),
  activities: document.querySelector("#activities"),
  activitiesContainer: document.querySelector("#activities-container"),
  activityPreview: document.querySelector("#activity-preview"),
  hideNoiseToggle: document.querySelector("#hide-noise-toggle"),
  clearActivitiesBtn: document.querySelector("#clear-activities-btn"),
  activityCollapseBtn: document.querySelector("#activity-collapse-btn"),
  activityHeaderToggle: document.querySelector("#activity-header-toggle"),
  meetingForm: document.querySelector("#meeting-form"),
  meetingTitle: document.querySelector("#meeting-title"),
  meetingTranscript: document.querySelector("#meeting-transcript"),
  meetingTargetDate: document.querySelector("#meeting-target-date"),
  meetingList: document.querySelector("#meeting-list"),
  meetingIdBadge: document.querySelector("#meeting-id-badge"),
  meetingSummary: document.querySelector("#meeting-summary"),
  meetingDecisions: document.querySelector("#meeting-decisions"),
  meetingPrioritiesOverview: document.querySelector("#meeting-priorities-overview"),
  executionHealthLabel: document.querySelector("#execution-health-label"),
  executionProgressLabel: document.querySelector("#execution-progress-label"),
  executionProgressBar: document.querySelector("#execution-progress-bar"),
  nextRecommendation: document.querySelector("#next-recommendation"),
  adaptationNote: document.querySelector("#adaptation-note"),
  actionCount: document.querySelector("#action-count"),
  priorityHighPreview: document.querySelector("#priority-high-preview"),
  priorityMediumPreview: document.querySelector("#priority-medium-preview"),
  priorityLowPreview: document.querySelector("#priority-low-preview"),
  priorityHigh: document.querySelector("#priority-high"),
  priorityMedium: document.querySelector("#priority-medium"),
  priorityLow: document.querySelector("#priority-low"),
  bucketToday: document.querySelector("#bucket-today"),
  bucketTomorrow: document.querySelector("#bucket-tomorrow"),
  bucketThisWeek: document.querySelector("#bucket-this-week"),
  bucketNextWeek: document.querySelector("#bucket-next-week"),
  bucketLater: document.querySelector("#bucket-later"),
  copilotSpeakerBadge: document.querySelector("#copilot-speaker-badge"),
  copilotQuestion: document.querySelector("#copilot-question"),
  copilotAnswer: document.querySelector("#copilot-answer"),
  copilotMeetingTitle: document.querySelector("#copilot-meeting-title"),
  copilotScreenSignal: document.querySelector("#copilot-screen-signal"),
  copilotTone: document.querySelector("#copilot-tone"),
  copilotPoints: document.querySelector("#copilot-points"),
  copilotScreenContext: document.querySelector("#copilot-screen-context"),
  copilotTaskContext: document.querySelector("#copilot-task-context"),
  copilotFollowUp: document.querySelector("#copilot-follow-up"),
  refreshCopilotBtn: document.querySelector("#refresh-copilot-btn"),
  floatingCopilot: document.querySelector("#floating-copilot"),
  floatingHeader: document.querySelector(".floating-copilot-header"),
  floatingBody: document.querySelector("#floating-copilot-body"),
  floatingOpenBtn: document.querySelector("#floating-open-btn"),
  floatingToggleBtn: document.querySelector("#floating-toggle-btn"),
  floatingAskBtn: document.querySelector("#floating-ask-btn"),
  floatingSummaryBtn: document.querySelector("#floating-summary-btn"),
  floatingTasksBtn: document.querySelector("#floating-tasks-btn"),
  floatingRefreshBtn: document.querySelector("#floating-refresh-btn"),
  floatingCommandText: document.querySelector("#floating-command-text"),
  floatingSpeakerChip: document.querySelector("#floating-speaker-chip"),
  floatingToneChip: document.querySelector("#floating-tone-chip"),
  floatingModeChip: document.querySelector("#floating-mode-chip"),
  floatingQuestion: document.querySelector("#floating-question"),
  floatingAnswer: document.querySelector("#floating-answer"),
  floatingScreenContext: document.querySelector("#floating-screen-context"),
  floatingFollowUp: document.querySelector("#floating-follow-up"),
  templates: {
    plannerAction: document.querySelector("#planner-action-template"),
    plannerPreview: document.querySelector("#planner-preview-template"),
    meetingList: document.querySelector("#meeting-list-template"),
    task: document.querySelector("#task-template"),
    activity: document.querySelector("#activity-template"),
  },
};

const viewIds = ["overview", "planner", "boards", "copilot", "signals"];
const timelineTargets = {
  today: el.bucketToday,
  tomorrow: el.bucketTomorrow,
  "this week": el.bucketThisWeek,
  "next week": el.bucketNextWeek,
  later: el.bucketLater,
};

function sentenceCase(value) {
  if (!value) {
    return "";
  }
  return value
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function healthLabel(value) {
  return sentenceCase(value || "needs_start");
}

function formatTimestamp(value) {
  if (!value) {
    return "No timestamp";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function truncate(value, maxLength = 180) {
  if (!value) {
    return "";
  }
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 1).trimEnd()}…`;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json();
}

function setActiveView(viewName) {
  if (!viewIds.includes(viewName)) {
    return;
  }

  state.activeView = viewName;
  el.navButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.viewTarget === viewName);
  });

  el.views.forEach((panel) => {
    panel.classList.toggle("active", panel.id === `view-${viewName}`);
  });
}

function setEmpty(container, message) {
  container.innerHTML = `<p class="body-text empty">${message}</p>`;
}

function normalizeBucket(bucket) {
  const value = (bucket || "Later").trim().toLowerCase();
  if (value === "this week" || value === "today" || value === "tomorrow" || value === "next week" || value === "later") {
    return value;
  }
  return "later";
}

function latestQuestionFromTranscript(transcript) {
  if (!transcript) {
    return { speaker: "No speaker", question: "" };
  }

  const lines = transcript
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  for (let index = lines.length - 1; index >= 0; index -= 1) {
    const line = lines[index];
    if (!line.includes("?")) {
      continue;
    }

    const match = line.match(/^([^:]+):\s*(.+)$/);
    if (match) {
      return { speaker: match[1].trim(), question: match[2].trim() };
    }

    return { speaker: "Meeting", question: line };
  }

  return { speaker: "No speaker", question: "" };
}

function summarizeScreenSignal() {
  const [activity] = state.dashboard.activities || [];
  if (!activity) {
    return "No recent screen activity.";
  }

  return truncate(activity.inferred_summary || activity.ocr_text || `${activity.app_name} ${activity.window_title}`, 120);
}

function summarizeTaskSignal() {
  const openTasks = (state.dashboard.tasks || []).filter((task) => task.status !== "done");
  if (!openTasks.length) {
    return "No open tasks available.";
  }

  const preview = openTasks.slice(0, 2).map((task) => task.title).join("; ");
  return truncate(preview, 120);
}

function buildCopilotPayload(mode = state.copilotMode) {
  const meeting = state.activeMeeting;
  const { speaker, question } = latestQuestionFromTranscript(meeting?.transcript || "");
  const screenSignal = summarizeScreenSignal();
  const taskSignal = summarizeTaskSignal();
  const nextRecommendation = meeting?.next_recommendation || "Use the latest signal and move to the next concrete action.";
  const tone = mode === "summary" ? "Executive" : mode === "tasks" ? "Directive" : "Concise";

  let answer = "Load a meeting plan to generate a response.";
  let followUp = "Open a meeting plan to unlock the copilot context.";
  let points = [];

  if (meeting) {
    if (mode === "summary") {
      answer = truncate(
        `${meeting.summary} Right now the plan health is ${healthLabel(meeting.execution_health).toLowerCase()} and the next move is ${nextRecommendation}`,
        260,
      );
      followUp = meeting.adaptation_note || nextRecommendation;
      points = [
        "Summarize the outcome first.",
        "Call out the current execution health.",
        "Finish with the recommended next move.",
      ];
    } else if (mode === "tasks") {
      const tasks = meeting.actions.slice(0, 3).map((action) => `${action.title} (${sentenceCase(action.timeline_bucket)})`);
      answer = tasks.length
        ? `Focus the room on these next actions: ${tasks.join("; ")}.`
        : "No saved action items yet. Generate a plan from a transcript first.";
      followUp = "Ask whether the room agrees on owners and due windows.";
      points = [
        "Name the first action clearly.",
        "Confirm owner and timeline.",
        "Check for blockers before you move on.",
      ];
    } else {
      answer = truncate(
        [
          question ? `Answer the question directly: ${question}` : "Lead with the core product point.",
          meeting.summary,
          `Ground the response in the current signal: ${screenSignal}`,
        ].join(" "),
        280,
      );
      followUp = meeting.next_recommendation || "Close by proposing the next concrete step.";
      points = [
        "State the product difference in one sentence.",
        "Connect it to the current screen or work signal.",
        "End with the next concrete execution step.",
      ];
    }
  }

  return {
    speaker,
    question: question || "No meeting question detected yet.",
    answer,
    tone,
    followUp,
    points,
    screenSignal,
    taskSignal,
    mode,
    meetingTitle: meeting?.title || "None loaded",
  };
}

function renderSessionStatus() {
  const active = Boolean(state.session.active);
  el.heroStatusPill.textContent = active ? "Live" : "Idle";
  el.heroStatusPill.className = `status-pill ${active ? "live" : "paused"}`;
  el.watcherStatus.textContent = state.session.label || (active ? "Live session" : "Session idle");
  el.watcherToggle.textContent = active ? "Stop session" : "Start session";
}

function renderStats() {
  const tasks = state.dashboard.tasks || [];
  const activities = state.dashboard.activities || [];
  const meetings = state.meetings || [];

  el.statOpenTasks.textContent = `${tasks.filter((task) => task.status !== "done").length}`;
  el.statMeetings.textContent = `${meetings.length}`;
  el.statActivities.textContent = `${activities.length}`;
  el.statActivitiesMeta.textContent = state.includeNoise ? "Full feed" : "Noise filtered feed";
}

function renderTaskList() {
  const tasks = state.dashboard.tasks || [];
  el.tasks.innerHTML = "";

  if (!tasks.length) {
    setEmpty(el.tasks, "No tasks yet. The seeded demo dataset will appear on first run, or generate tasks from a live session.");
    return;
  }

  tasks.forEach((task) => {
    const fragment = el.templates.task.content.cloneNode(true);
    const card = fragment.querySelector(".signal-task-card");
    const view = fragment.querySelector(".signal-task-view");
    const title = fragment.querySelector(".card-title");
    const status = fragment.querySelector(".task-status-pill");
    const priority = fragment.querySelector(".task-priority-chip");
    const timeline = fragment.querySelector(".task-timeline-chip");
    const meta = fragment.querySelector(".card-meta");
    const body = fragment.querySelector(".card-body");
    const editButton = fragment.querySelector(".task-edit-btn");
    const completeButton = fragment.querySelector(".task-complete-btn");
    const form = fragment.querySelector(".task-edit-form");
    const titleInput = fragment.querySelector(".task-title-input");
    const priorityInput = fragment.querySelector(".task-priority-input");
    const timelineInput = fragment.querySelector(".task-timeline-input");
    const statusInput = fragment.querySelector(".task-status-input");
    const reasonInput = fragment.querySelector(".task-reason-input");
    const cancelButton = fragment.querySelector(".task-cancel-btn");

    title.textContent = task.title;
    status.textContent = sentenceCase(task.status);
    status.classList.add(task.status);
    priority.textContent = sentenceCase(task.priority);
    priority.classList.add(`priority-${task.priority}`);
    timeline.textContent = sentenceCase(task.timeline_bucket);
    meta.textContent = `${task.source_window || "Manual"} • ${task.confidence}% confidence • ${formatTimestamp(task.created_at)}`;
    body.textContent = task.reason || "No rationale available.";
    completeButton.textContent = task.status === "done" ? "Reopen" : "Mark done";
    view.classList.toggle("is-done", task.status === "done");

    titleInput.value = task.title;
    priorityInput.value = task.priority;
    timelineInput.value = task.timeline_bucket;
    statusInput.value = task.status;
    reasonInput.value = task.reason || "";

    editButton.addEventListener("click", () => {
      view.classList.add("hidden");
      form.classList.remove("hidden");
    });

    cancelButton.addEventListener("click", () => {
      form.classList.add("hidden");
      view.classList.remove("hidden");
    });

    completeButton.addEventListener("click", async () => {
      const nextStatus = task.status === "done" ? "open" : "done";
      await fetchJson(`/api/tasks/${task.id}`, {
        method: "PUT",
        body: JSON.stringify({
          title: task.title,
          priority: task.priority,
          timeline_bucket: task.timeline_bucket,
          status: nextStatus,
          reason: task.reason || "",
        }),
      });
      await refreshDashboard();
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await fetchJson(`/api/tasks/${task.id}`, {
        method: "PUT",
        body: JSON.stringify({
          title: titleInput.value.trim(),
          priority: priorityInput.value,
          timeline_bucket: timelineInput.value,
          status: statusInput.value,
          reason: reasonInput.value.trim(),
        }),
      });
      await refreshDashboard();
    });

    el.tasks.appendChild(fragment);
  });
}

function renderActivities() {
  const activities = state.dashboard.activities || [];
  el.activities.innerHTML = "";

  if (!activities.length) {
    setEmpty(el.activities, "No activity yet. Start a session or trigger a manual scan.");
    return;
  }

  activities.forEach((activity) => {
    const fragment = el.templates.activity.content.cloneNode(true);
    const title = fragment.querySelector(".card-title");
    const meta = fragment.querySelector(".card-meta");
    const body = fragment.querySelector(".card-body");
    const deleteButton = fragment.querySelector(".activity-delete-btn");

    title.textContent = activity.window_title || "Untitled activity";
    meta.textContent = `${activity.app_name || "Unknown app"} • ${activity.confidence}% confidence • ${formatTimestamp(activity.created_at)}`;
    body.textContent = truncate(activity.inferred_summary || activity.ocr_text || "No OCR content stored.", 220);

    deleteButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      await fetchJson(`/api/activities/${activity.id}`, { method: "DELETE" });
      await refreshDashboard();
    });

    el.activities.appendChild(fragment);
  });

  el.activitiesContainer.classList.toggle("hidden", state.activityCollapsed);
  el.activityCollapseBtn.textContent = state.activityCollapsed ? "Expand" : "Collapse";
}

function renderActivityPreview() {
  const activities = (state.dashboard.activities || []).slice(0, 3);
  el.activityPreview.innerHTML = "";

  if (!activities.length) {
    setEmpty(el.activityPreview, "No recent activity.");
    return;
  }

  activities.forEach((activity) => {
    const card = document.createElement("article");
    card.className = "planner-preview-card";
    card.innerHTML = `
      <h4 class="planner-preview-title"></h4>
      <p class="card-meta"></p>
    `;
    card.querySelector(".planner-preview-title").textContent = activity.window_title || activity.app_name || "Signal";
    card.querySelector(".card-meta").textContent = truncate(activity.inferred_summary || activity.ocr_text || "No OCR signal.", 120);
    el.activityPreview.appendChild(card);
  });
}

function renderMeetingList() {
  el.meetingList.innerHTML = "";

  if (!state.meetings.length) {
    setEmpty(el.meetingList, "No saved meetings yet. Generate one from a transcript.");
    return;
  }

  state.meetings.forEach((meeting) => {
    const fragment = el.templates.meetingList.content.cloneNode(true);
    const item = fragment.querySelector(".meeting-list-item");
    const title = fragment.querySelector(".meeting-list-title");
    const meta = fragment.querySelector(".meeting-list-meta");
    const button = fragment.querySelector(".meeting-open-btn");

    title.textContent = meeting.title;
    meta.textContent = `${healthLabel(meeting.execution_health)} • ${meeting.progress_percent || 0}% • ${meeting.target_end_date || "No target date"}`;
    item.classList.toggle("active", state.activeMeeting?.id === meeting.id);

    button.addEventListener("click", () => {
      void loadMeeting(meeting.id);
    });

    el.meetingList.appendChild(fragment);
  });
}

function renderExecutionHealth(meeting) {
  const progress = Math.max(0, Math.min(100, meeting?.progress_percent || 0));
  const health = meeting?.execution_health || "needs_start";

  el.executionHealthLabel.textContent = healthLabel(health);
  el.executionHealthLabel.className = `execution-health-label health-${health}`;
  el.executionProgressLabel.textContent = `${progress}%`;
  el.executionProgressBar.style.width = `${progress}%`;
  el.executionProgressBar.className = `progress-fill health-${health}`;
  el.nextRecommendation.textContent = meeting?.next_recommendation || "Generate or open a plan to see the next move.";
  el.adaptationNote.textContent = meeting?.adaptation_note || "No execution state yet.";
}

function createPreviewCard(action) {
  const fragment = el.templates.plannerPreview.content.cloneNode(true);
  fragment.querySelector(".planner-preview-title").textContent = action.title;
  const priorityChip = fragment.querySelector(".preview-priority-chip");
  const timelineChip = fragment.querySelector(".preview-timeline-chip");
  priorityChip.textContent = sentenceCase(action.priority);
  priorityChip.classList.add(`preview-priority-${action.priority}`);
  timelineChip.textContent = sentenceCase(action.timeline_bucket);
  return fragment;
}

function createActionCard(action) {
  const fragment = el.templates.plannerAction.content.cloneNode(true);
  const card = fragment.querySelector(".planner-task-card");
  const title = fragment.querySelector(".planner-task-title");
  const body = fragment.querySelector(".planner-task-body");
  const ownerChip = fragment.querySelector(".owner-chip");
  const priorityChip = fragment.querySelector(".priority-chip");
  const timelineChip = fragment.querySelector(".timeline-chip");
  const timeChip = fragment.querySelector(".time-chip");
  const riskChip = fragment.querySelector(".risk-chip");
  const blockedChip = fragment.querySelector(".blocked-chip");
  const button = fragment.querySelector(".planner-complete-btn");

  title.textContent = action.title;
  ownerChip.textContent = action.owner || "Unassigned";
  priorityChip.textContent = sentenceCase(action.priority);
  priorityChip.classList.add(`priority-${action.priority}`);
  timelineChip.textContent = sentenceCase(action.timeline_bucket);
  timeChip.textContent = `${action.estimated_minutes || 0} min`;
  riskChip.textContent = `Risk: ${sentenceCase(action.risk_level)}`;
  riskChip.classList.add(`risk-${action.risk_level}`);
  blockedChip.textContent = action.is_blocked ? "Blocked" : "Ready";
  blockedChip.classList.add(action.is_blocked ? "blocked" : "ready");
  body.textContent = truncate(
    [action.rationale, action.dependency_summary ? `Dependency: ${action.dependency_summary}` : "", action.unblocker ? `Unblocker: ${action.unblocker}` : ""]
      .filter(Boolean)
      .join(" "),
    260,
  );

  card.classList.toggle("done", action.status === "done");
  button.textContent = action.status === "done" ? "Reopen" : "Mark done";
  button.addEventListener("click", async () => {
    if (!state.activeMeeting) {
      return;
    }
    await fetchJson(`/api/meetings/${state.activeMeeting.id}/actions/${action.id}/status`, {
      method: "POST",
      body: JSON.stringify({ status: action.status === "done" ? "open" : "done" }),
    });
    await loadMeeting(state.activeMeeting.id);
    await refreshMeetings(false);
  });

  return fragment;
}

function renderBoards() {
  const meeting = state.activeMeeting;
  const previews = {
    high: el.priorityHighPreview,
    medium: el.priorityMediumPreview,
    low: el.priorityLowPreview,
  };
  const boards = {
    high: el.priorityHigh,
    medium: el.priorityMedium,
    low: el.priorityLow,
  };

  Object.values(previews).forEach((node) => { node.innerHTML = ""; });
  Object.values(boards).forEach((node) => { node.innerHTML = ""; });
  Object.values(timelineTargets).forEach((node) => { node.innerHTML = ""; });

  if (!meeting || !meeting.actions.length) {
    Object.values(previews).forEach((node) => setEmpty(node, "No items."));
    Object.values(boards).forEach((node) => setEmpty(node, "No items."));
    Object.values(timelineTargets).forEach((node) => setEmpty(node, "No items."));
    el.actionCount.textContent = "0 actions";
    return;
  }

  const actions = [...meeting.actions].sort((a, b) => a.step_order - b.step_order);
  el.actionCount.textContent = `${actions.length} actions`;

  ["high", "medium", "low"].forEach((priority) => {
    const filtered = actions.filter((action) => action.priority === priority);
    if (!filtered.length) {
      setEmpty(previews[priority], "No items.");
      setEmpty(boards[priority], "No items.");
      return;
    }

    filtered.slice(0, 2).forEach((action) => previews[priority].appendChild(createPreviewCard(action)));
    filtered.forEach((action) => boards[priority].appendChild(createActionCard(action)));
  });

  Object.entries(timelineTargets).forEach(([bucket, container]) => {
    const filtered = actions.filter((action) => normalizeBucket(action.timeline_bucket) === bucket);
    if (!filtered.length) {
      setEmpty(container, "No items.");
      return;
    }
    filtered.forEach((action) => container.appendChild(createActionCard(action)));
  });
}

function renderMeetingDetails() {
  const meeting = state.activeMeeting;

  if (!meeting) {
    el.meetingIdBadge.textContent = "No plan yet";
    el.meetingSummary.textContent = "No summary yet.";
    el.meetingDecisions.textContent = "No decisions yet.";
    el.meetingPrioritiesOverview.textContent = "No priorities yet.";
    renderExecutionHealth(null);
    renderBoards();
    return;
  }

  el.meetingIdBadge.textContent = `Plan #${meeting.id}`;
  el.meetingSummary.textContent = meeting.summary || "No summary yet.";
  el.meetingDecisions.textContent = meeting.decisions || "No decisions yet.";
  el.meetingPrioritiesOverview.textContent = meeting.priorities_overview || "No priorities yet.";
  renderExecutionHealth(meeting);
  renderBoards();
}

function renderCopilot() {
  const payload = buildCopilotPayload();
  const modeLabel = payload.mode === "summary" ? "Summary mode" : payload.mode === "tasks" ? "Task mode" : "Answer mode";
  const speakerText = payload.speaker && payload.speaker !== "No speaker" ? `${payload.speaker} asked` : "No question yet";

  el.copilotSpeakerBadge.textContent = speakerText;
  el.copilotQuestion.textContent = payload.question;
  el.copilotAnswer.textContent = payload.answer;
  el.copilotMeetingTitle.textContent = payload.meetingTitle;
  el.copilotScreenSignal.textContent = payload.screenSignal;
  el.copilotTone.textContent = payload.tone;
  el.copilotScreenContext.textContent = payload.screenSignal;
  el.copilotTaskContext.textContent = payload.taskSignal;
  el.copilotFollowUp.textContent = payload.followUp;

  el.copilotPoints.innerHTML = "";
  if (!payload.points.length) {
    setEmpty(el.copilotPoints, "No talking points yet.");
  } else {
    payload.points.forEach((point, index) => {
      const card = document.createElement("article");
      card.className = "copilot-point-card";
      card.innerHTML = `
        <h4 class="copilot-point-title">Point ${index + 1}</h4>
        <p class="copilot-point-body"></p>
      `;
      card.querySelector(".copilot-point-body").textContent = point;
      el.copilotPoints.appendChild(card);
    });
  }

  el.floatingCommandText.textContent =
    payload.mode === "summary" ? "Summarize the room" : payload.mode === "tasks" ? "What should we do next?" : "What should I say next?";
  el.floatingSpeakerChip.textContent = payload.speaker || "No speaker";
  el.floatingToneChip.textContent = payload.tone;
  el.floatingModeChip.textContent = modeLabel;
  el.floatingQuestion.textContent = payload.question;
  el.floatingAnswer.textContent = payload.answer;
  el.floatingScreenContext.textContent = payload.screenSignal;
  el.floatingFollowUp.textContent = payload.followUp;

  [el.floatingAskBtn, el.floatingSummaryBtn, el.floatingTasksBtn].forEach((button) => button.classList.remove("active"));
  if (payload.mode === "summary") {
    el.floatingSummaryBtn.classList.add("active");
  } else if (payload.mode === "tasks") {
    el.floatingTasksBtn.classList.add("active");
  } else {
    el.floatingAskBtn.classList.add("active");
  }
}

function updateFloatingLayout() {
  el.floatingCopilot.classList.toggle("minimized", state.floatingMinimized);
  el.floatingToggleBtn.textContent = state.floatingMinimized ? "Show" : "Hide";

  if (!state.floatingPosition) {
    el.floatingCopilot.style.left = "";
    el.floatingCopilot.style.top = "";
    el.floatingCopilot.style.bottom = "";
    el.floatingCopilot.style.transform = "";
    return;
  }

  el.floatingCopilot.style.left = `${state.floatingPosition.left}px`;
  el.floatingCopilot.style.top = `${state.floatingPosition.top}px`;
  el.floatingCopilot.style.bottom = "auto";
  el.floatingCopilot.style.transform = "none";
}

async function refreshDashboard() {
  state.dashboard = await fetchJson(`/api/dashboard?include_noise=${state.includeNoise}&activity_limit=20`);
  renderStats();
  renderTaskList();
  renderActivities();
  renderActivityPreview();
  renderCopilot();
}

async function refreshMeetings(loadActive = true) {
  state.meetings = await fetchJson("/api/meetings");
  renderStats();
  renderMeetingList();

  if (loadActive) {
    const activeId = state.activeMeeting?.id || state.meetings[0]?.id;
    if (activeId) {
      await loadMeeting(activeId);
    } else {
      state.activeMeeting = null;
      renderMeetingDetails();
      renderCopilot();
    }
  }
}

async function loadMeeting(meetingId) {
  state.activeMeeting = await fetchJson(`/api/meetings/${meetingId}`);
  renderMeetingList();
  renderMeetingDetails();
  renderCopilot();
}

async function refreshSession() {
  state.session = await fetchJson("/api/session/status");
  renderSessionStatus();
}

async function handleSessionToggle() {
  const url = state.session.active ? "/api/session/stop" : "/api/session/start";
  state.session = await fetchJson(url, { method: "POST" });
  renderSessionStatus();
}

async function handleScanNow() {
  await fetchJson("/api/scan-once", { method: "POST" });
  setTimeout(() => {
    void refreshDashboard();
  }, 1200);
}

async function handleMeetingSubmit(event) {
  event.preventDefault();
  const payload = {
    title: el.meetingTitle.value.trim(),
    transcript: el.meetingTranscript.value.trim(),
    target_end_date: el.meetingTargetDate.value || null,
  };

  if (!payload.title || !payload.transcript) {
    return;
  }

  const meeting = await fetchJson("/api/meetings/plan", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  state.activeMeeting = meeting;
  await refreshMeetings(false);
  renderMeetingList();
  renderMeetingDetails();
  renderCopilot();
  setActiveView("overview");
  el.meetingForm.reset();
}

function setupNavigation() {
  el.navButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveView(button.dataset.viewTarget);
    });
  });

  el.shortcutViewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveView(button.dataset.shortcutView);
    });
  });
}

function setupActivityControls() {
  el.hideNoiseToggle.checked = !state.includeNoise;
  el.hideNoiseToggle.addEventListener("change", async () => {
    state.includeNoise = !el.hideNoiseToggle.checked;
    await refreshDashboard();
  });

  el.clearActivitiesBtn.addEventListener("click", async () => {
    await fetchJson("/api/activities/clear", { method: "POST" });
    await refreshDashboard();
  });

  el.activityHeaderToggle.addEventListener("click", (event) => {
    if (event.target.closest("button") || event.target.closest("label")) {
      return;
    }
    state.activityCollapsed = !state.activityCollapsed;
    renderActivities();
  });

  el.activityCollapseBtn.addEventListener("click", () => {
    state.activityCollapsed = !state.activityCollapsed;
    renderActivities();
  });
}

function setCopilotMode(mode) {
  state.copilotMode = mode;
  renderCopilot();
}

function setupCopilotControls() {
  el.refreshCopilotBtn.addEventListener("click", () => renderCopilot());
  el.floatingRefreshBtn.addEventListener("click", () => renderCopilot());
  el.floatingOpenBtn.addEventListener("click", () => setActiveView("copilot"));
  el.floatingToggleBtn.addEventListener("click", () => {
    state.floatingMinimized = !state.floatingMinimized;
    updateFloatingLayout();
  });
  el.floatingAskBtn.addEventListener("click", () => setCopilotMode("answer"));
  el.floatingSummaryBtn.addEventListener("click", () => setCopilotMode("summary"));
  el.floatingTasksBtn.addEventListener("click", () => setCopilotMode("tasks"));

  let dragState = null;

  el.floatingHeader.addEventListener("pointerdown", (event) => {
    if (event.target.closest("button")) {
      return;
    }
    const rect = el.floatingCopilot.getBoundingClientRect();
    dragState = {
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    };
    el.floatingHeader.setPointerCapture(event.pointerId);
    if (!state.floatingPosition) {
      state.floatingPosition = { left: rect.left, top: rect.top };
    }
  });

  el.floatingHeader.addEventListener("pointermove", (event) => {
    if (!dragState) {
      return;
    }
    state.floatingPosition = {
      left: Math.max(12, event.clientX - dragState.offsetX),
      top: Math.max(12, event.clientY - dragState.offsetY),
    };
    updateFloatingLayout();
  });

  const stopDragging = () => {
    dragState = null;
  };

  el.floatingHeader.addEventListener("pointerup", stopDragging);
  el.floatingHeader.addEventListener("pointercancel", stopDragging);

  document.addEventListener("keydown", (event) => {
    if (event.key === "/") {
      const activeTag = document.activeElement?.tagName;
      if (activeTag !== "INPUT" && activeTag !== "TEXTAREA" && activeTag !== "SELECT") {
        event.preventDefault();
        el.floatingCopilot.focus();
      }
    }

    if (event.key === "1") {
      setCopilotMode("answer");
    } else if (event.key === "2") {
      setCopilotMode("summary");
    } else if (event.key === "3") {
      setCopilotMode("tasks");
    }

    if (document.activeElement !== el.floatingCopilot) {
      return;
    }

    if (!state.floatingPosition) {
      const rect = el.floatingCopilot.getBoundingClientRect();
      state.floatingPosition = { left: rect.left, top: rect.top };
    }

    const step = event.shiftKey ? 24 : 12;
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      state.floatingPosition.left = Math.max(12, state.floatingPosition.left - step);
      updateFloatingLayout();
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      state.floatingPosition.left += step;
      updateFloatingLayout();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      state.floatingPosition.top = Math.max(12, state.floatingPosition.top - step);
      updateFloatingLayout();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      state.floatingPosition.top += step;
      updateFloatingLayout();
    } else if (event.key.toLowerCase() === "m") {
      event.preventDefault();
      state.floatingMinimized = !state.floatingMinimized;
      updateFloatingLayout();
    } else if (event.key.toLowerCase() === "c") {
      event.preventDefault();
      setActiveView("copilot");
    }
  });
}

async function initialize() {
  setupNavigation();
  setupActivityControls();
  setupCopilotControls();

  el.watcherToggle.addEventListener("click", () => {
    void handleSessionToggle();
  });
  el.scanNow.addEventListener("click", () => {
    void handleScanNow();
  });
  el.meetingForm.addEventListener("submit", (event) => {
    void handleMeetingSubmit(event);
  });

  await refreshSession();
  await refreshDashboard();
  await refreshMeetings();
  updateFloatingLayout();

  window.setInterval(() => {
    void refreshSession();
  }, 10000);

  window.setInterval(() => {
    void refreshDashboard();
  }, 15000);

  window.setInterval(() => {
    void refreshMeetings(false);
  }, 30000);
}

void initialize();
