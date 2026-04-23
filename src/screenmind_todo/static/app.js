const watcherStatusEl = document.querySelector("#watcher-status");
const watcherToggleBtn = document.querySelector("#watcher-toggle");
const scanNowBtn = document.querySelector("#scan-now");
const heroStatusPillEl = document.querySelector("#hero-status-pill");

const tasksEl = document.querySelector("#tasks");
const activitiesEl = document.querySelector("#activities");
const taskTemplate = document.querySelector("#task-template");
const activityTemplate = document.querySelector("#activity-template");

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

const meetingListEl = document.querySelector("#meeting-list");
const meetingListTemplate = document.querySelector("#meeting-list-template");
const plannerActionTemplate = document.querySelector("#planner-action-template");
const actionCountEl = document.querySelector("#action-count");

const activityContainer = document.querySelector("#activities-container");
const activityCollapseBtn = document.querySelector("#activity-collapse-btn");
const activityHeaderToggle = document.querySelector("#activity-header-toggle");

const statOpenTasksEl = document.querySelector("#stat-open-tasks");
const statMeetingsEl = document.querySelector("#stat-meetings");
const statActivitiesEl = document.querySelector("#stat-activities");
const statActivitiesMetaEl = document.querySelector("#stat-activities-meta");

let activeMeetingId = null;
let hideNoise = true;
let activityCollapsed = false;
let latestDashboard = { tasks: [], activities: [] };
let latestMeetings = [];

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

function setActivityCollapsed(collapsed) {
  activityCollapsed = collapsed;

  if (!activityContainer || !activityCollapseBtn) {
    return;
  }

  activityContainer.style.display = collapsed ? "none" : "block";
  activityCollapseBtn.textContent = collapsed ? "Expand" : "Collapse";
}

function toggleActivityPanel() {
  setActivityCollapsed(!activityCollapsed);
}

function updateDashboardStats() {
  const taskCount = latestDashboard.tasks.length;
  const activityCount = latestDashboard.activities.length;
  const meetingCount = latestMeetings.length;

  if (statOpenTasksEl) {
    statOpenTasksEl.textContent = `${taskCount}`;
  }

  if (statMeetingsEl) {
    statMeetingsEl.textContent = `${meetingCount}`;
  }

  if (statActivitiesEl) {
    statActivitiesEl.textContent = `${activityCount}`;
  }

  if (statActivitiesMetaEl) {
    statActivitiesMetaEl.textContent = hideNoise ? "Noise filtered feed" : "Showing all captured items";
  }
}

function setEmptyState(container, message) {
  container.innerHTML = `<p class="empty">${message}</p>`;
}

async function fetchWatcherStatus() {
  const data = await fetchJson("/api/watcher/status");
  const enabled = Boolean(data.enabled);

  watcherStatusEl.textContent = enabled ? "Watcher: ON" : "Watcher: PAUSED";
  watcherToggleBtn.textContent = enabled ? "Stop watcher" : "Start watcher";
  watcherToggleBtn.dataset.mode = enabled ? "stop" : "start";

  if (heroStatusPillEl) {
    heroStatusPillEl.textContent = enabled ? "Live" : "Paused";
    heroStatusPillEl.classList.toggle("live", enabled);
    heroStatusPillEl.classList.toggle("paused", !enabled);
  }
}

async function fetchDashboard() {
  const includeNoise = hideNoise ? "false" : "true";
  const data = await fetchJson(`/api/dashboard?include_noise=${includeNoise}&activity_limit=20`);
  const tasks = data.tasks || [];
  const activities = data.activities || [];

  latestDashboard = { tasks, activities };
  updateDashboardStats();

  renderScreenTasks(tasks);
  renderActivities(activities);

  if (activities.length === 0) {
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

async function fetchMeetings() {
  const meetings = await fetchJson("/api/meetings");
  latestMeetings = meetings || [];
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
    });

    meetingListEl.appendChild(node);
  });
}

function clearPlannerBoards() {
  priorityHighEl.innerHTML = "";
  priorityMediumEl.innerHTML = "";
  priorityLowEl.innerHTML = "";

  bucketTodayEl.innerHTML = "";
  bucketTomorrowEl.innerHTML = "";
  bucketThisWeekEl.innerHTML = "";
  bucketNextWeekEl.innerHTML = "";
  bucketLaterEl.innerHTML = "";
}

function createPlannerActionCard(action, meetingId) {
  const fragment = plannerActionTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".planner-task-card");
  card.querySelector(".planner-task-title").textContent = action.title;
  card.querySelector(".planner-task-meta").textContent =
    `${action.owner} • ${action.priority.toUpperCase()} • ${action.timeline_bucket} • ${action.estimated_minutes} min`;
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

function ensureLaneEmptyStates(actions) {
  if (!actions.length) {
    setEmptyState(priorityHighEl, "No actions.");
    setEmptyState(priorityMediumEl, "No actions.");
    setEmptyState(priorityLowEl, "No actions.");
    setEmptyState(bucketTodayEl, "No items.");
    setEmptyState(bucketTomorrowEl, "No items.");
    setEmptyState(bucketThisWeekEl, "No items.");
    setEmptyState(bucketNextWeekEl, "No items.");
    setEmptyState(bucketLaterEl, "No items.");
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
  ].forEach((container) => {
    if (!container.children.length) {
      setEmptyState(container, "No items.");
    }
  });
}

function renderMeetingDetails(meeting) {
  activeMeetingId = meeting.id;
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

    if (priorityTarget) priorityTarget.appendChild(priorityCard);
    if (timelineTarget) timelineTarget.appendChild(timelineCard);
  });

  ensureLaneEmptyStates(actions);
}

function getPriorityContainer(priority) {
  const normalized = (priority || "").toLowerCase();
  if (normalized === "high") return priorityHighEl;
  if (normalized === "medium") return priorityMediumEl;
  return priorityLowEl;
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

if (clearActivitiesBtn) {
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
}

if (hideNoiseToggle) {
  hideNoiseToggle.checked = true;
  hideNoiseToggle.addEventListener("change", async () => {
    hideNoise = hideNoiseToggle.checked;
    await fetchDashboard();
  });
}

if (activityCollapseBtn) {
  activityCollapseBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleActivityPanel();
  });
}

if (activityHeaderToggle) {
  activityHeaderToggle.addEventListener("click", (event) => {
    if (event.target.closest("button") || event.target.closest("input") || event.target.closest("label")) {
      return;
    }
    toggleActivityPanel();
  });
}

async function initialize() {
  setActivityCollapsed(false);
  await Promise.all([fetchWatcherStatus(), fetchDashboard(), fetchMeetings()]);
}

initialize();
setInterval(fetchDashboard, 12000);
setInterval(fetchWatcherStatus, 12000);
setInterval(fetchMeetings, 15000);
