const ADMIN_TOKEN_KEY = "bingo_admin_token";

function getAdminToken() {
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

function setAdminToken(token) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
}

function clearAdminSession() {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
  window.location.href = "./login.html";
}

function requireAdmin() {
  if (!getAdminToken()) {
    window.location.href = "./login.html";
    return false;
  }
  return true;
}

async function adminFetch(url, options = {}) {
  const token = getAdminToken();
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401 || res.status === 403) {
    clearAdminSession();
    return null;
  }
  return res;
}

function markAdminNavLink() {
  const currentPage = window.location.pathname.split("/").pop();
  document.querySelectorAll(".admin-nav-link").forEach((link) => {
    const linkPage = link.getAttribute("href")?.split("/").pop();
    link.classList.toggle("is-active", linkPage === currentPage);
  });
}

const logoutBtn = document.querySelector("#adminLogout");
if (logoutBtn) {
  logoutBtn.addEventListener("click", clearAdminSession);
}

markAdminNavLink();
