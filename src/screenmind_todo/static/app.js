const watcherStatusEl = document.querySelector("#watcher-status");
const watcherToggleBtn = document.querySelector("#watcher-toggle");
const scanNowBtn = document.querySelector("#scan-now");
const heroStatusPillEl = document.querySelector("#hero-status-pill");

const tasksEl = document.querySelector("#tasks");
const activitiesEl = document.querySelector("#activities");
const activityPreviewEl = document.querySelector("#activity-preview");
const taskTemplate = document.querySelector("#task-template");
const activityTemplate = document.querySelector("#activity-template");
const refreshCopilotBtn = document.querySelector("#refresh-copilot-btn");
const floatingCopilotEl = document.querySelector("#floating-copilot");
const floatingCopilotBodyEl = document.querySelector("#floating-copilot-body");
const floatingRefreshBtn = document.querySelector("#floating-refresh-btn");
const floatingOpenBtn = document.querySelector("#floating-open-btn");
const floatingToggleBtn = document.querySelector("#floating-toggle-btn");

const clearActivitiesBtn = document.querySelector("#clear-activities-btn");
const hideNoiseToggle = document.querySelector("#hide-noise-toggle");

const meetingForm = document.querySelector("#meeting-form");
const meetingTitleInput = document.querySelector("#meeting-title");
const meetingTranscriptInput = document.querySelector("#meeting-transcript");
const meetingTargetDateInput = document.querySelector("#meeting-target-date");
const generatePlanBtn = document.querySelector("#generate-plan-btn");

const meetingSummaryEl = document.querySelector("#meeting-summary");
const meetingDecisionsEl = document.querySelector("#meeting-decisions");
const meetingPrioritiesOverviewEl = document.querySelector("#meeting-priorities-overview");
const meetingIdBadgeEl = document.querySelector("#meeting-id-badge");

const priorityHighEl = document.querySelector("#priority-high");
const priorityMediumEl = document.querySelector("#priority-medium");
const priorityLowEl = document.querySelector("#priority-low");

const bucketTodayEl = document.querySelector("#bucket-today");
const bucketTomorrowEl = document.querySelector("#bucket-tomorrow");
const bucketThisWeekEl = document.querySelector("#bucket-this-week");
const bucketNextWeekEl = document.querySelector("#bucket-next-week");
const bucketLaterEl = document.querySelector("#bucket-later");

const priorityHighPreviewEl = document.querySelector("#priority-high-preview");
const priorityMediumPreviewEl = document.querySelector("#priority-medium-preview");
const priorityLowPreviewEl = document.querySelector("#priority-low-preview");

const meetingListEl = document.querySelector("#meeting-list");
const meetingListTemplate = document.querySelector("#meeting-list-template");
const plannerActionTemplate = document.querySelector("#planner-action-template");
const plannerPreviewTemplate = document.querySelector("#planner-preview-template");
const actionCountEl = document.querySelector("#action-count");

const activityContainer = document.querySelector("#activities-container");
const activityCollapseBtn = document.querySelector("#activity-collapse-btn");
const activityHeaderToggle = document.querySelector("#activity-header-toggle");

const statOpenTasksEl = document.querySelector("#stat-open-tasks");
const statMeetingsEl = document.querySelector("#stat-meetings");
const statActivitiesEl = document.querySelector("#stat-activities");
const statActivitiesMetaEl = document.querySelector("#stat-activities-meta");

const copilotSpeakerBadgeEl = document.querySelector("#copilot-speaker-badge");
const copilotQuestionEl = document.querySelector("#copilot-question");
const copilotAnswerEl = document.querySelector("#copilot-answer");
const copilotMeetingTitleEl = document.querySelector("#copilot-meeting-title");
const copilotScreenSignalEl = document.querySelector("#copilot-screen-signal");
const copilotToneEl = document.querySelector("#copilot-tone");
const copilotPointsEl = document.querySelector("#copilot-points");
const copilotScreenContextEl = document.querySelector("#copilot-screen-context");
const copilotTaskContextEl = document.querySelector("#copilot-task-context");
const copilotFollowUpEl = document.querySelector("#copilot-follow-up");
const floatingSpeakerChipEl = document.querySelector("#floating-speaker-chip");
const floatingToneChipEl = document.querySelector("#floating-tone-chip");
const floatingQuestionEl = document.querySelector("#floating-question");
const floatingAnswerEl = document.querySelector("#floating-answer");
const floatingScreenContextEl = document.querySelector("#floating-screen-context");
const floatingFollowUpEl = document.querySelector("#floating-follow-up");

const navButtons = [...document.querySelectorAll(".nav-pill[data-view-target]")];
const shortcutViewButtons = [...document.querySelectorAll("[data-shortcut-view]")];
const viewPanels = [...document.querySelectorAll(".view-panel")];

let activeMeetingId = null;
let activeMeetingDetails = null;
let hideNoise = true;
let activityCollapsed = false;
let latestDashboard = { tasks: [], activities: [] };
let latestMeetings = [];
let activeView = "overview";
let floatingCopilotMinimized = false;

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${url}`);
  }
  return response.json();
}

function formatDateTime(value) {
  if (!value) return "No timestamp";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatDate(value) {
  if (!value) return "No target date";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function sentenceCase(value) {
  if (!value) return "Unknown";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function setEmptyState(container, message) {
  container.innerHTML = `<p class="empty">${message}</p>`;
}

function truncateText(value, maxLength = 160) {
  if (!value) return "";
  return value.length > maxLength ? `${value.slice(0, maxLength).trim()}...` : value;
}

function extractLatestQuestion(transcript) {
  if (!transcript) {
    return null;
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

    const speakerMatch = line.match(/^([A-Za-z][A-Za-z .'-]{1,40}):\s*(.+)$/);
    if (speakerMatch) {
      return {
        speaker: speakerMatch[1].trim(),
        question: speakerMatch[2].trim()
      };
    }

    return {
      speaker: "Meeting participant",
      question: line
    };
  }

  const sentences = transcript
    .split(/(?<=[.?!])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean);

  const fallbackQuestion = [...sentences].reverse().find((sentence) => sentence.includes("?"));
  if (!fallbackQuestion) {
    return null;
  }

  return {
    speaker: "Meeting participant",
    question: fallbackQuestion
  };
}

function summarizeScreenSignal() {
  const latestActivity = latestDashboard.activities[0];
  if (!latestActivity) {
    return "No recent activity captured.";
  }

  return truncateText(
    latestActivity.inferred_summary || latestActivity.window_title || latestActivity.ocr_text || "Screen activity",
    140
  );
}

function summarizeTaskSignal() {
  const openTasks = latestDashboard.tasks.filter((task) => (task.status || "").toLowerCase() !== "done");
  if (!openTasks.length) {
    return "No open watcher tasks available.";
  }

  return openTasks
    .slice(0, 2)
    .map((task) => task.title)
    .join(" | ");
}

function buildCopilotResponse() {
  if (!activeMeetingDetails) {
    return {
      speaker: "No meeting loaded",
      question: "No meeting question detected yet.",
      answer: "Open a saved meeting or generate a meeting plan to get a suggested answer.",
      meetingTitle: "None loaded",
      screenSignal: summarizeScreenSignal(),
      tone: "Concise",
      points: [],
      screenContext: summarizeScreenSignal(),
      taskContext: summarizeTaskSignal(),
      followUp: "Load a meeting plan to generate the next-response guidance."
    };
  }

  const latestQuestion = extractLatestQuestion(activeMeetingDetails.transcript);
  const openActions = (activeMeetingDetails.actions || []).filter(
    (action) => (action.status || "").toLowerCase() !== "done"
  );
  const nextAction = openActions[0];
  const screenSignal = summarizeScreenSignal();
  const taskSignal = summarizeTaskSignal();
  const meetingTitle = activeMeetingDetails.title || "Untitled meeting";
  const speaker = latestQuestion?.speaker || "Meeting participant";
  const question = latestQuestion?.question || "No explicit question detected in the transcript.";
  const tone = nextAction?.priority?.toLowerCase() === "high" ? "Direct" : "Calm";

  const answerParts = [];
  if (latestQuestion) {
    answerParts.push(`I would answer ${speaker} by grounding the response in the current plan for ${meetingTitle}.`);
  } else {
    answerParts.push(`I would give a short progress update tied to the plan for ${meetingTitle}.`);
  }
  if (nextAction) {
    answerParts.push(
      `The clearest next step is ${nextAction.title.toLowerCase()}, which is currently ${nextAction.timeline_bucket.toLowerCase()} and marked ${nextAction.priority.toLowerCase()} priority.`
    );
  }
  if (screenSignal && screenSignal !== "No recent activity captured.") {
    answerParts.push(`Your screen suggests the immediate context is ${screenSignal.toLowerCase()}.`);
  }
  answerParts.push("Close by confirming the next owner, timing, and what decision you need from the room.");

  const points = [
    {
      title: "Anchor on the plan",
      body: activeMeetingDetails.summary || "Use the meeting summary to restate the goal before answering."
    },
    nextAction
      ? {
          title: "Lead with the next action",
          body: `${nextAction.title} is the strongest concrete item to mention next.`
        }
      : null,
    {
      title: "Use current screen context",
      body: screenSignal
    },
    {
      title: "Reference live workload",
      body: taskSignal
    }
  ].filter(Boolean);

  return {
    speaker,
    question,
    answer: answerParts.join(" "),
    meetingTitle,
    screenSignal,
    tone,
    points,
    screenContext: screenSignal,
    taskContext: taskSignal,
    followUp: nextAction
      ? `Finish by asking for confirmation on ${nextAction.title.toLowerCase()} and whether the due timing still holds.`
      : "Ask whether the room wants a concrete next action or a decision summary."
  };
}

function renderCopilot() {
  const data = buildCopilotResponse();

  copilotSpeakerBadgeEl.textContent = data.speaker;
  copilotQuestionEl.textContent = data.question;
  copilotAnswerEl.textContent = data.answer;
  copilotMeetingTitleEl.textContent = data.meetingTitle;
  copilotScreenSignalEl.textContent = data.screenSignal;
  copilotToneEl.textContent = data.tone;
  copilotScreenContextEl.textContent = data.screenContext;
  copilotTaskContextEl.textContent = data.taskContext;
  copilotFollowUpEl.textContent = data.followUp;

  floatingSpeakerChipEl.textContent = data.speaker;
  floatingToneChipEl.textContent = data.tone;
  floatingQuestionEl.textContent = data.question;
  floatingAnswerEl.textContent = data.answer;
  floatingScreenContextEl.textContent = data.screenContext;
  floatingFollowUpEl.textContent = data.followUp;

  copilotPointsEl.innerHTML = "";
  if (!data.points.length) {
    setEmptyState(copilotPointsEl, "No talking points yet.");
    return;
  }

  data.points.forEach((point) => {
    const card = document.createElement("article");
    card.className = "copilot-point-card";
    card.innerHTML = `
      <h4 class="copilot-point-title">${point.title}</h4>
      <p class="copilot-point-body">${point.body}</p>
    `;
    copilotPointsEl.appendChild(card);
  });
}

function setFloatingCopilotMinimized(minimized) {
  floatingCopilotMinimized = minimized;
  floatingCopilotEl.classList.toggle("minimized", minimized);
  floatingToggleBtn.textContent = minimized ? "Expand" : "Minimize";

  if (floatingCopilotBodyEl) {
    floatingCopilotBodyEl.setAttribute("aria-hidden", minimized ? "true" : "false");
  }
}

function setActivityCollapsed(collapsed) {
  activityCollapsed = collapsed;

  if (!activityContainer || !activityCollapseBtn) {
    return;
  }

  activityContainer.style.display = collapsed ? "none" : "block";
  activityCollapseBtn.textContent = collapsed ? "Expand" : "Collapse";
}

function setActiveView(viewName) {
  activeView = viewName;

  navButtons.forEach((button) => {
    const isActive = button.dataset.viewTarget === viewName;
    button.classList.toggle("active", isActive);
  });

  viewPanels.forEach((panel) => {
    panel.classList.toggle("active", panel.id === `view-${viewName}`);
  });
}

function toggleActivityPanel() {
  setActivityCollapsed(!activityCollapsed);
}

function updateDashboardStats() {
  const taskCount = latestDashboard.tasks.length;
  const activityCount = latestDashboard.activities.length;
  const meetingCount = latestMeetings.length;

  statOpenTasksEl.textContent = `${taskCount}`;
  statMeetingsEl.textContent = `${meetingCount}`;
  statActivitiesEl.textContent = `${activityCount}`;
  statActivitiesMetaEl.textContent = hideNoise ? "Noise filtered feed" : "Showing all captured items";
}

async function fetchWatcherStatus() {
  const data = await fetchJson("/api/watcher/status");
  const enabled = Boolean(data.enabled);

  watcherStatusEl.textContent = enabled ? "Watcher: ON" : "Watcher: PAUSED";
  watcherToggleBtn.textContent = enabled ? "Stop watcher" : "Start watcher";
  watcherToggleBtn.dataset.mode = enabled ? "stop" : "start";

  heroStatusPillEl.textContent = enabled ? "Live" : "Paused";
  heroStatusPillEl.classList.toggle("live", enabled);
  heroStatusPillEl.classList.toggle("paused", !enabled);
}

async function fetchDashboard() {
  const includeNoise = hideNoise ? "false" : "true";
  const data = await fetchJson(`/api/dashboard?include_noise=${includeNoise}&activity_limit=20`);
  latestDashboard = {
    tasks: data.tasks || [],
    activities: data.activities || []
  };

  updateDashboardStats();
  renderScreenTasks(latestDashboard.tasks);
  renderActivities(latestDashboard.activities);
  renderActivityPreview(latestDashboard.activities);
  renderCopilot();

  if (!latestDashboard.activities.length) {
    setActivityCollapsed(true);
  }
}

function renderScreenTasks(tasks) {
  tasksEl.innerHTML = "";

  if (!tasks.length) {
    setEmptyState(tasksEl, "No screen watcher tasks yet.");
    return;
  }

  tasks.forEach((task) => {
    const node = taskTemplate.content.cloneNode(true);
    node.querySelector(".card-title").textContent = task.title;
    node.querySelector(".card-meta").textContent =
      `${task.source_window || "Unknown source"} • confidence ${task.confidence}%`;
    node.querySelector(".card-body").textContent = task.reason || "No reason recorded.";

    const statusPill = node.querySelector(".task-status-pill");
    const normalizedStatus = (task.status || "open").toLowerCase();
    statusPill.textContent = sentenceCase(normalizedStatus);
    statusPill.classList.add(normalizedStatus === "done" ? "done" : "open");

    tasksEl.appendChild(node);
  });
}

function renderActivities(activities) {
  activitiesEl.innerHTML = "";

  if (!activities.length) {
    setEmptyState(activitiesEl, "No activity captured yet.");
    return;
  }

  activities.forEach((activity) => {
    const node = activityTemplate.content.cloneNode(true);
    node.querySelector(".card-title").textContent =
      activity.inferred_summary || activity.window_title || "Screen activity";
    node.querySelector(".card-meta").textContent =
      `${activity.app_name || "Unknown app"} • confidence ${activity.confidence ?? 0}% • ${formatDateTime(activity.created_at)}`;
    node.querySelector(".card-body").textContent = activity.ocr_text || "No OCR text stored.";

    const deleteBtn = node.querySelector(".activity-delete-btn");
    deleteBtn.addEventListener("click", async () => {
      try {
        await fetchJson(`/api/activities/${activity.id}`, { method: "DELETE" });
        await fetchDashboard();
      } catch (error) {
        console.error("Delete activity failed:", error);
        alert("Failed to delete activity.");
      }
    });

    activitiesEl.appendChild(node);
  });
}

function renderActivityPreview(activities) {
  activityPreviewEl.innerHTML = "";

  const previewItems = activities.slice(0, 3);
  if (!previewItems.length) {
    setEmptyState(activityPreviewEl, "No recent signal yet.");
    return;
  }

  previewItems.forEach((activity) => {
    const card = document.createElement("article");
    card.className = "activity-item-card";
    card.innerHTML = `
      <h4 class="card-title">${activity.inferred_summary || activity.window_title || "Screen activity"}</h4>
      <p class="card-meta">${activity.app_name || "Unknown app"} • ${formatDateTime(activity.created_at)}</p>
      <p class="card-body">${activity.ocr_text || "No OCR text stored."}</p>
    `;
    activityPreviewEl.appendChild(card);
  });
}

async function fetchMeetings() {
  latestMeetings = await fetchJson("/api/meetings");
  updateDashboardStats();
  renderMeetingList(latestMeetings);

  if (!activeMeetingId && latestMeetings.length > 0) {
    const details = await fetchJson(`/api/meetings/${latestMeetings[0].id}`);
    activeMeetingId = latestMeetings[0].id;
    renderMeetingDetails(details);
  }
}

function renderMeetingList(meetings) {
  meetingListEl.innerHTML = "";

  if (!meetings.length) {
    setEmptyState(meetingListEl, "No meeting plans created yet.");
    return;
  }

  meetings.forEach((meeting) => {
    const node = meetingListTemplate.content.cloneNode(true);
    node.querySelector(".meeting-list-title").textContent = meeting.title;
    node.querySelector(".meeting-list-meta").textContent =
      `${formatDate(meeting.target_end_date)} • ${formatDateTime(meeting.created_at)}`;

    node.querySelector(".meeting-open-btn").addEventListener("click", async () => {
      const details = await fetchJson(`/api/meetings/${meeting.id}`);
      activeMeetingId = meeting.id;
      renderMeetingDetails(details);
      setActiveView("overview");
    });

    meetingListEl.appendChild(node);
  });
}

function clearPlannerBoards() {
  [
    priorityHighEl,
    priorityMediumEl,
    priorityLowEl,
    bucketTodayEl,
    bucketTomorrowEl,
    bucketThisWeekEl,
    bucketNextWeekEl,
    bucketLaterEl,
    priorityHighPreviewEl,
    priorityMediumPreviewEl,
    priorityLowPreviewEl,
  ].forEach((element) => {
    element.innerHTML = "";
  });
}

function createPlannerActionCard(action, meetingId) {
  const fragment = plannerActionTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".planner-task-card");
  card.querySelector(".planner-task-title").textContent = action.title;

  const chips = card.querySelectorAll(".planner-chip");
  chips[0].textContent = action.owner || "Unassigned";
  chips[1].textContent = sentenceCase(action.priority);
  chips[1].classList.add(`priority-${(action.priority || "low").toLowerCase()}`);
  chips[2].textContent = action.timeline_bucket || "Later";
  chips[3].textContent = `${action.estimated_minutes} min`;

  card.querySelector(".planner-task-body").textContent =
    `${action.rationale}${action.due_date ? ` Due: ${action.due_date}.` : ""}`;

  const btn = card.querySelector(".planner-complete-btn");
  if (action.status === "done") {
    btn.textContent = "Done";
    btn.disabled = true;
  } else {
    btn.addEventListener("click", async () => {
      try {
        const updatedMeeting = await fetchJson(
          `/api/meetings/${meetingId}/actions/${action.id}/status`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: "done" })
          }
        );
        renderMeetingDetails(updatedMeeting);
        await fetchMeetings();
      } catch (error) {
        console.error("Mark action done failed:", error);
        alert("Failed to update action.");
      }
    });
  }

  return card;
}

function createPlannerPreviewCard(action) {
  const fragment = plannerPreviewTemplate.content.cloneNode(true);
  fragment.querySelector(".planner-preview-title").textContent = action.title;

  const priorityChip = fragment.querySelector(".preview-priority-chip");
  priorityChip.textContent = sentenceCase(action.priority);
  priorityChip.classList.add(`preview-priority-${(action.priority || "low").toLowerCase()}`);

  fragment.querySelector(".preview-timeline-chip").textContent = action.timeline_bucket || "Later";
  return fragment;
}

function ensureLaneEmptyStates(actions) {
  if (!actions.length) {
    [
      priorityHighEl,
      priorityMediumEl,
      priorityLowEl,
      bucketTodayEl,
      bucketTomorrowEl,
      bucketThisWeekEl,
      bucketNextWeekEl,
      bucketLaterEl,
      priorityHighPreviewEl,
      priorityMediumPreviewEl,
      priorityLowPreviewEl,
    ].forEach((container) => setEmptyState(container, "No items."));
    return;
  }

  [
    priorityHighEl,
    priorityMediumEl,
    priorityLowEl,
    bucketTodayEl,
    bucketTomorrowEl,
    bucketThisWeekEl,
    bucketNextWeekEl,
    bucketLaterEl,
    priorityHighPreviewEl,
    priorityMediumPreviewEl,
    priorityLowPreviewEl,
  ].forEach((container) => {
    if (!container.children.length) {
      setEmptyState(container, "No items.");
    }
  });
}

function renderMeetingDetails(meeting) {
  activeMeetingId = meeting.id;
  activeMeetingDetails = meeting;
  meetingIdBadgeEl.textContent = `Meeting #${meeting.id}`;
  meetingSummaryEl.textContent = meeting.summary || "No summary available.";
  meetingDecisionsEl.textContent = meeting.decisions || "No decisions available.";
  meetingPrioritiesOverviewEl.textContent =
    meeting.priorities_overview || "No priority overview available.";

  clearPlannerBoards();

  const actions = (meeting.actions || []).slice().sort((a, b) => a.step_order - b.step_order);
  actionCountEl.textContent = `${actions.length} actions`;

  actions.forEach((action) => {
    const priorityCard = createPlannerActionCard(action, meeting.id);
    const timelineCard = createPlannerActionCard(action, meeting.id);

    const priorityTarget = getPriorityContainer(action.priority);
    const timelineTarget = getTimelineContainer(action.timeline_bucket);
    const previewTarget = getPriorityPreviewContainer(action.priority);

    if (priorityTarget) {
      priorityTarget.appendChild(priorityCard);
    }
    if (timelineTarget) {
      timelineTarget.appendChild(timelineCard);
    }
    if (previewTarget && previewTarget.children.length < 2) {
      previewTarget.appendChild(createPlannerPreviewCard(action));
    }
  });

  ensureLaneEmptyStates(actions);
  renderCopilot();
}

function getPriorityContainer(priority) {
  const normalized = (priority || "").toLowerCase();
  if (normalized === "high") return priorityHighEl;
  if (normalized === "medium") return priorityMediumEl;
  return priorityLowEl;
}

function getPriorityPreviewContainer(priority) {
  const normalized = (priority || "").toLowerCase();
  if (normalized === "high") return priorityHighPreviewEl;
  if (normalized === "medium") return priorityMediumPreviewEl;
  return priorityLowPreviewEl;
}

function getTimelineContainer(bucket) {
  const normalized = (bucket || "").toLowerCase();
  if (normalized === "today") return bucketTodayEl;
  if (normalized === "tomorrow") return bucketTomorrowEl;
  if (normalized === "this week") return bucketThisWeekEl;
  if (normalized === "next week") return bucketNextWeekEl;
  return bucketLaterEl;
}

meetingForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const title = meetingTitleInput.value.trim();
  const transcript = meetingTranscriptInput.value.trim();
  const target_end_date = meetingTargetDateInput.value || null;

  if (!title || !transcript) return;

  try {
    generatePlanBtn.disabled = true;
    generatePlanBtn.textContent = "Generating...";

    const meeting = await fetchJson("/api/meetings/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        transcript,
        target_end_date
      })
    });

    renderMeetingDetails(meeting);
    await fetchMeetings();
    meetingForm.reset();
    setActiveView("overview");
  } catch (error) {
    console.error("Meeting plan generation failed:", error);
    alert("Failed to generate meeting plan.");
  } finally {
    generatePlanBtn.disabled = false;
    generatePlanBtn.textContent = "Generate plan";
  }
});

scanNowBtn.addEventListener("click", async () => {
  try {
    scanNowBtn.disabled = true;
    scanNowBtn.textContent = "Scanning...";
    await fetchJson("/api/scan-once", { method: "POST" });
    await fetchDashboard();
    await fetchWatcherStatus();
  } catch (error) {
    console.error("Scan failed:", error);
  } finally {
    scanNowBtn.disabled = false;
    scanNowBtn.textContent = "Scan now";
  }
});

watcherToggleBtn.addEventListener("click", async () => {
  try {
    watcherToggleBtn.disabled = true;
    const mode = watcherToggleBtn.dataset.mode || "stop";
    const endpoint = mode === "stop" ? "/api/watcher/stop" : "/api/watcher/start";
    await fetchJson(endpoint, { method: "POST" });
    await fetchWatcherStatus();
  } catch (error) {
    console.error("Watcher toggle failed:", error);
  } finally {
    watcherToggleBtn.disabled = false;
  }
});

clearActivitiesBtn.addEventListener("click", async () => {
  try {
    clearActivitiesBtn.disabled = true;
    clearActivitiesBtn.textContent = "Clearing...";
    await fetchJson("/api/activities/clear", { method: "POST" });
    await fetchDashboard();
  } catch (error) {
    console.error("Failed to clear activities:", error);
    alert("Failed to clear activities.");
  } finally {
    clearActivitiesBtn.disabled = false;
    clearActivitiesBtn.textContent = "Clear all";
  }
});

hideNoiseToggle.checked = true;
hideNoiseToggle.addEventListener("change", async () => {
  hideNoise = hideNoiseToggle.checked;
  await fetchDashboard();
});

activityCollapseBtn.addEventListener("click", (event) => {
  event.stopPropagation();
  toggleActivityPanel();
});

activityHeaderToggle.addEventListener("click", (event) => {
  if (event.target.closest("button") || event.target.closest("input") || event.target.closest("label")) {
    return;
  }
  toggleActivityPanel();
});

navButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setActiveView(button.dataset.viewTarget);
  });
});

shortcutViewButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setActiveView(button.dataset.shortcutView);
  });
});

refreshCopilotBtn.addEventListener("click", () => {
  renderCopilot();
});

floatingRefreshBtn.addEventListener("click", () => {
  renderCopilot();
});

floatingOpenBtn.addEventListener("click", () => {
  setActiveView("copilot");
});

floatingToggleBtn.addEventListener("click", () => {
  setFloatingCopilotMinimized(!floatingCopilotMinimized);
});

async function initialize() {
  setActivityCollapsed(false);
  setActiveView(activeView);
  setFloatingCopilotMinimized(false);
  renderCopilot();
  await Promise.all([fetchWatcherStatus(), fetchDashboard(), fetchMeetings()]);
}

initialize();
setInterval(fetchDashboard, 12000);
setInterval(fetchWatcherStatus, 12000);
setInterval(fetchMeetings, 15000);
