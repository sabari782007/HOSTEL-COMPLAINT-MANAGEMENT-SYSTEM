/* =====================================================
   Hostel Complaint Management System — Frontend logic
   Talks to the Flask REST API defined in backend/app.py
   ===================================================== */

const API_BASE = "http://127.0.0.1:5000/api";

let currentUser = JSON.parse(localStorage.getItem("hcms_user") || "null");

// ---------------------------------------------------
// Element refs
// ---------------------------------------------------
const authView = document.getElementById("authView");
const appView = document.getElementById("appView");
const userBadge = document.getElementById("userBadge");
const userName = document.getElementById("userName");

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const loginError = document.getElementById("loginError");
const registerError = document.getElementById("registerError");

const categorySelect = document.getElementById("categorySelect");
const complaintForm = document.getElementById("complaintForm");
const complaintSuccess = document.getElementById("complaintSuccess");

const myComplaintsList = document.getElementById("myComplaintsList");
const adminList = document.getElementById("adminList");
const filterStatus = document.getElementById("filterStatus");

const statusModal = document.getElementById("statusModal");
const statusForm = document.getElementById("statusForm");
const modalComplaintId = document.getElementById("modalComplaintId");

let categories = [];
let activeComplaintForModal = null;

// ---------------------------------------------------
// Helpers
// ---------------------------------------------------
async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function statusClass(status) {
  return "status-pill--" + status.toLowerCase().replace(" ", "-");
}

function stubClass(status, priority) {
  let cls = "stub";
  if (status === "Resolved") cls += " stub--resolved";
  if (status === "Rejected") cls += " stub--rejected";
  if (priority === "High") cls += " stub--high";
  return cls;
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso.includes("Z") ? iso : iso + "Z");
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

// ---------------------------------------------------
// Auth: tab switching
// ---------------------------------------------------
document.querySelectorAll(".tabs:not(.tabs--app) .tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tabs:not(.tabs--app) .tab").forEach((t) => t.classList.remove("tab--active"));
    tab.classList.add("tab--active");
    const isLogin = tab.dataset.tab === "login";
    loginForm.hidden = !isLogin;
    registerForm.hidden = isLogin;
  });
});

// ---------------------------------------------------
// Login / Register
// ---------------------------------------------------
loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.textContent = "";
  const fd = new FormData(loginForm);
  try {
    const data = await api("/login", {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(fd)),
    });
    currentUser = data.user;
    localStorage.setItem("hcms_user", JSON.stringify(currentUser));
    enterApp();
  } catch (err) {
    loginError.textContent = err.message;
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  registerError.textContent = "";
  const fd = new FormData(registerForm);
  try {
    await api("/register", {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(fd)),
    });
    registerError.style.color = "var(--green)";
    registerError.textContent = "Account created — you can log in now.";
    registerForm.reset();
  } catch (err) {
    registerError.style.color = "var(--red)";
    registerError.textContent = err.message;
  }
});

document.getElementById("logoutBtn").addEventListener("click", () => {
  currentUser = null;
  localStorage.removeItem("hcms_user");
  appView.hidden = true;
  userBadge.hidden = true;
  authView.hidden = false;
});

// ---------------------------------------------------
// App view switching
// ---------------------------------------------------
function enterApp() {
  authView.hidden = true;
  appView.hidden = false;
  userBadge.hidden = false;
  userName.textContent = `${currentUser.full_name} · ${currentUser.role}`;

  const isAdmin = currentUser.role === "admin";
  document.querySelectorAll(".tab--admin").forEach((t) => (t.hidden = !isAdmin));

  loadCategories();
  showView("newComplaint");
  loadMyComplaints();
}

document.querySelectorAll(".tabs--app .tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tabs--app .tab").forEach((t) => t.classList.remove("tab--active"));
    tab.classList.add("tab--active");
    showView(tab.dataset.view);
  });
});

function showView(id) {
  document.querySelectorAll(".panel").forEach((p) => (p.hidden = p.id !== id));
  if (id === "myComplaints") loadMyComplaints();
  if (id === "adminBoard") loadAdminBoard();
  if (id === "reports") loadReports();
}

// ---------------------------------------------------
// Categories
// ---------------------------------------------------
async function loadCategories() {
  try {
    categories = await api("/categories");
    categorySelect.innerHTML = categories
      .map((c) => `<option value="${c.category_id}">${c.name}</option>`)
      .join("");
  } catch (err) {
    console.error(err);
  }
}

// ---------------------------------------------------
// New complaint
// ---------------------------------------------------
complaintForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  complaintSuccess.textContent = "";
  const fd = new FormData(complaintForm);
  const payload = Object.fromEntries(fd);
  payload.student_id = currentUser.user_id;

  try {
    await api("/complaints", { method: "POST", body: JSON.stringify(payload) });
    complaintSuccess.textContent = "Complaint submitted successfully.";
    complaintForm.reset();
  } catch (err) {
    complaintSuccess.style.color = "var(--red)";
    complaintSuccess.textContent = err.message;
  }
});

// ---------------------------------------------------
// My complaints (student view)
// ---------------------------------------------------
async function loadMyComplaints() {
  myComplaintsList.innerHTML = "Loading…";
  try {
    const rows = await api(`/complaints?student_id=${currentUser.user_id}`);
    if (!rows.length) {
      myComplaintsList.innerHTML = `<p style="color:var(--text-muted)">No complaints raised yet.</p>`;
      return;
    }
    myComplaintsList.innerHTML = rows.map(renderStub).join("");
  } catch (err) {
    myComplaintsList.innerHTML = `<p class="form__error">${err.message}</p>`;
  }
}

// ---------------------------------------------------
// Admin board
// ---------------------------------------------------
filterStatus.addEventListener("change", loadAdminBoard);
document.getElementById("refreshBoard").addEventListener("click", loadAdminBoard);

async function loadAdminBoard() {
  adminList.innerHTML = "Loading…";
  const status = filterStatus.value;
  try {
    const rows = await api(`/complaints${status ? `?status=${status}` : ""}`);
    if (!rows.length) {
      adminList.innerHTML = `<p style="color:var(--text-muted)">No complaints found.</p>`;
      return;
    }
    adminList.innerHTML = rows.map((r) => renderStub(r, true)).join("");
    adminList.querySelectorAll("[data-update]").forEach((btn) => {
      btn.addEventListener("click", () => openStatusModal(btn.dataset.update));
    });
  } catch (err) {
    adminList.innerHTML = `<p class="form__error">${err.message}</p>`;
  }
}

function renderStub(c, isAdmin = false) {
  return `
    <div class="${stubClass(c.status, c.priority)}">
      <div>
        <div class="stub__id">TICKET #${String(c.complaint_id).padStart(4, "0")} · ${c.category_name}</div>
        <div class="stub__title">${escapeHtml(c.title)}</div>
        <div class="stub__meta">
          <span>${c.block || "—"} ${c.room_number || ""}</span>
          <span>Filed ${fmtDate(c.created_at)}</span>
          ${isAdmin ? `<span>By ${escapeHtml(c.student_name)}</span>` : ""}
        </div>
        <div class="stub__desc">${escapeHtml(c.description)}</div>
        ${c.admin_remarks ? `<div class="stub__remarks">Remarks: ${escapeHtml(c.admin_remarks)}</div>` : ""}
        ${isAdmin ? `<div class="stub__actions"><button class="btn btn--ghost btn--sm" data-update="${c.complaint_id}">Update status</button></div>` : ""}
      </div>
      <span class="status-pill ${statusClass(c.status)}">${c.status}</span>
    </div>
  `;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---------------------------------------------------
// Status update modal
// ---------------------------------------------------
function openStatusModal(complaintId) {
  activeComplaintForModal = complaintId;
  modalComplaintId.textContent = String(complaintId).padStart(4, "0");
  statusModal.hidden = false;
}

document.getElementById("modalCancel").addEventListener("click", () => {
  statusModal.hidden = true;
});

statusForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(statusForm);
  const payload = Object.fromEntries(fd);
  payload.changed_by = currentUser.user_id;

  try {
    await api(`/complaints/${activeComplaintForModal}/status`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    statusModal.hidden = true;
    statusForm.reset();
    loadAdminBoard();
  } catch (err) {
    alert(err.message);
  }
});

// ---------------------------------------------------
// Reports
// ---------------------------------------------------
async function loadReports() {
  const el = document.getElementById("reportSummary");
  el.innerHTML = "Loading…";
  try {
    const data = await api("/reports/summary");
    const cards = [];
    data.by_status.forEach((s) =>
      cards.push(`<div class="report-card"><div class="report-card__num">${s.count}</div><div class="report-card__label">${s.status}</div></div>`)
    );
    data.by_category.forEach((c) =>
      cards.push(`<div class="report-card"><div class="report-card__num">${c.count}</div><div class="report-card__label">${c.category}</div></div>`)
    );
    if (data.average_rating) {
      cards.push(`<div class="report-card"><div class="report-card__num">${data.average_rating} ★</div><div class="report-card__label">Avg. feedback rating</div></div>`);
    }
    el.innerHTML = cards.join("");
  } catch (err) {
    el.innerHTML = `<p class="form__error">${err.message}</p>`;
  }
}

// ---------------------------------------------------
// Boot
// ---------------------------------------------------
if (currentUser) enterApp();
