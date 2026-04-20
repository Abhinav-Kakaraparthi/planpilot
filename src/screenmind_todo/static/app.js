console.log("APP JS LOADED");
const tasksEl = document.querySelector("#tasks");
const activitiesEl = document.querySelector("#activities");
const taskCountEl = document.querySelector("#task-count");
const activityCountEl = document.querySelector("#activity-count");
const taskForm = document.querySelector("#task-form");
const taskTitle = document.querySelector("#task-title");
const scanNowBtn = document.querySelector("#scan-now");
const watcherToggleBtn = document.querySelector("#watcher-toggle");
const watcherStatusEl = document.querySelector("#watcher-status");

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${url}`);
  }
  return response.json();
}

function renderTasks(tasks) {
  const template = document.querySelector("#task-template");
  tasksEl.innerHTML = "";
  taskCountEl.textContent = tasks.length;

  if (!tasks.length) {
    tasksEl.innerHTML = `<p class="empty">No tasks yet. Let the watcher run for a minute.</p>`;
    return;
  }

  tasks.forEach((task) => {
    const node = template.content.cloneNode(true);
    node.querySelector(".card-title").textContent = task.title || "Untitled task";
    node.querySelector(".card-meta").textContent =
      `${(task.status || "open").toUpperCase()} • confidence ${task.confidence ?? 0}%`;
    node.querySelector(".card-body").textContent =
      task.reason || "No reason recorded.";

    const button = node.querySelector(".complete-btn");
    if ((task.status || "").toLowerCase() === "done") {
      button.disabled = true;
      button.textContent = "Completed";
    } else {
      button.addEventListener("click", async () => {
        try {
          await fetchJson(`/api/tasks/${task.id}/complete`, { method: "POST" });
          await fetchDashboard();
        } catch (error) {
          console.error("Complete task failed:", error);
        }
      });
    }

    tasksEl.appendChild(node);
  });
}

function renderActivities(activities) {
  const template = document.querySelector("#activity-template");
  activitiesEl.innerHTML = "";
  activityCountEl.textContent = activities.length;

  if (!activities.length) {
    activitiesEl.innerHTML = `<p class="empty">No activity captured yet.</p>`;
    return;
  }

  activities.forEach((activity) => {
    const node = template.content.cloneNode(true);
    node.querySelector(".card-title").textContent =
      activity.inferred_summary || activity.window_title || "Screen activity";
    node.querySelector(".card-meta").textContent =
      `${activity.app_name || "unknown app"} • confidence ${activity.confidence ?? 0}%`;
    node.querySelector(".card-body").textContent =
      activity.ocr_text || "No OCR text stored.";
    activitiesEl.appendChild(node);
  });
}

async function fetchDashboard() {
  try {
    const data = await fetchJson("/api/dashboard");
    renderTasks(data.tasks || []);
    renderActivities(data.activities || []);
  } catch (error) {
    console.error("Dashboard load failed:", error);
    tasksEl.innerHTML = `<p class="empty">Failed to load tasks.</p>`;
    activitiesEl.innerHTML = `<p class="empty">Failed to load activity.</p>`;
  }
}

async function fetchWatcherStatus() {
  if (!watcherToggleBtn || !watcherStatusEl) return;

  try {
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
  } catch (error) {
    console.error("Watcher status failed:", error);
    watcherStatusEl.textContent = "Watcher: Unknown";
  }
}

if (taskForm) {
  taskForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const title = taskTitle.value.trim();
    if (!title) return;

    try {
      await fetchJson("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          confidence: 100,
          reason: "Manually added by user"
        }),
      });

      taskTitle.value = "";
      await fetchDashboard();
    } catch (error) {
      console.error("Create task failed:", error);
    }
  });
}

if (scanNowBtn) {
  scanNowBtn.addEventListener("click", async () => {
    try {
      scanNowBtn.disabled = true;
      scanNowBtn.textContent = "Scanning...";
      await fetchJson("/api/scan-once", { method: "POST" });
      await new Promise((resolve) => setTimeout(resolve, 1500));
      await fetchDashboard();
      await fetchWatcherStatus();
    } catch (error) {
      console.error("Scan failed:", error);
    } finally {
      scanNowBtn.disabled = false;
      scanNowBtn.textContent = "Scan Now";
    }
  });
}

if (watcherToggleBtn) {
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
}

async function initialize() {
  await fetchDashboard();
  await fetchWatcherStatus();
}

initialize();
setInterval(fetchDashboard, 10000);
setInterval(fetchWatcherStatus, 10000);