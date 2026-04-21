const watcherStatusEl = document.querySelector("#watcher-status");
const watcherToggleBtn = document.querySelector("#watcher-toggle");
const scanNowBtn = document.querySelector("#scan-now");

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

let activeMeetingId = null;
let hideNoise = true;
let activityCollapsed = false;

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${url}`);
  }
  return response.json();
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

async function fetchWatcherStatus() {
  const data = await fetchJson("/api/watcher/status");

  if (data.enabled) {
    watcherStatusEl.textContent = "Watcher: ON";
    watcherToggleBtn.textContent = "Stop Watching";
    watcherToggleBtn.dataset.mode = "stop";
  } else {
    watcherStatusEl.textContent = "Watcher: PAUSED";
    watcherToggleBtn.textContent = "Start Watching";
    watcherToggleBtn.dataset.mode = "start";
  }
}

async function fetchDashboard() {
  const query = hideNoise ? "false" : "true";
  const data = await fetchJson(`/api/dashboard?include_noise=${query}&activity_limit=20`);
  const tasks = data.tasks || [];
  const activities = data.activities || [];

  renderScreenTasks(tasks);
  renderActivities(activities);

  if (activities.length === 0) {
    setActivityCollapsed(true);
  }
}

function renderScreenTasks(tasks) {
  tasksEl.innerHTML = "";

  if (!tasks.length) {
    tasksEl.innerHTML = `<p class="empty">No screen watcher tasks yet.</p>`;
    return;
  }

  tasks.forEach((task) => {
    const node = taskTemplate.content.cloneNode(true);
    node.querySelector(".card-title").textContent = task.title;
    node.querySelector(".card-meta").textContent =
      `${task.status.toUpperCase()} • confidence ${task.confidence}%`;
    node.querySelector(".card-body").textContent =
      task.reason || "No reason recorded.";
    tasksEl.appendChild(node);
  });
}

function renderActivities(activities) {
  activitiesEl.innerHTML = "";

  if (!activities.length) {
    activitiesEl.innerHTML = `<p class="empty">No activity captured yet.</p>`;
    return;
  }

  activities.forEach((activity) => {
    const node = activityTemplate.content.cloneNode(true);
    node.querySelector(".card-title").textContent =
      activity.inferred_summary || activity.window_title || "Screen activity";
    node.querySelector(".card-meta").textContent =
      `${activity.app_name || "unknown app"} • confidence ${activity.confidence ?? 0}%`;
    node.querySelector(".card-body").textContent =
      activity.ocr_text || "No OCR text stored.";

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
  renderMeetingList(meetings || []);

  if (!activeMeetingId && meetings.length > 0) {
    const details = await fetchJson(`/api/meetings/${meetings[0].id}`);
    activeMeetingId = meetings[0].id;
    renderMeetingDetails(details);
  }
}

function renderMeetingList(meetings) {
  meetingListEl.innerHTML = "";

  if (!meetings.length) {
    meetingListEl.innerHTML = `<p class="empty">No meeting plans created yet.</p>`;
    return;
  }

  meetings.forEach((meeting) => {
    const node = meetingListTemplate.content.cloneNode(true);
    node.querySelector(".meeting-list-title").textContent = meeting.title;
    node.querySelector(".meeting-list-meta").textContent =
      `${meeting.target_end_date || "No target date"} • ${new Date(meeting.created_at).toLocaleString()}`;

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

  if (!actions.length) {
    priorityHighEl.innerHTML = `<p class="empty">No actions.</p>`;
    bucketThisWeekEl.innerHTML = `<p class="empty">No timeline items.</p>`;
    return;
  }

  actions.forEach((action) => {
    const priorityCard = createPlannerActionCard(action, meeting.id);
    const timelineCard = createPlannerActionCard(action, meeting.id);

    const priorityTarget = getPriorityContainer(action.priority);
    const timelineTarget = getTimelineContainer(action.timeline_bucket);

    if (priorityTarget) priorityTarget.appendChild(priorityCard);
    if (timelineTarget) timelineTarget.appendChild(timelineCard);
  });
}

function getPriorityContainer(priority) {
  const p = (priority || "").toLowerCase();
  if (p === "high") return priorityHighEl;
  if (p === "medium") return priorityMediumEl;
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
    generatePlanBtn.textContent = "Generate Plan";
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
    scanNowBtn.textContent = "Scan Now";
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
      clearActivitiesBtn.textContent = "Clear All";
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
  await Promise.all([
    fetchWatcherStatus(),
    fetchDashboard(),
    fetchMeetings(),
  ]);
}

initialize();
setInterval(fetchDashboard, 12000);
setInterval(fetchWatcherStatus, 12000);
setInterval(fetchMeetings, 15000);