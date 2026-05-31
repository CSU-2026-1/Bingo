const USER_API_URL = "";
const LOGIN_PAGE_URL = "./login.html";

const profileStatus = document.querySelector("#profileStatus");
const profileUsername = document.querySelector("#profileUsername");
const profileEmail = document.querySelector("#profileEmail");
const profileBalance = document.querySelector("#profileBalance");
const profileAuthId = document.querySelector("#profileAuthId");
const profileEditButton = document.querySelector("#profileEditButton");
const profileEditForm = document.querySelector("#profileEditForm");
const profileCancelButton = document.querySelector("#profileCancelButton");
const logoutButton = document.querySelector("#logoutButton");

let currentProfile = null;

function readCachedUser() {
  try {
    return JSON.parse(localStorage.getItem("bingo_user") || "null");
  } catch {
    return null;
  }
}

function renderProfile(data) {
  if (!data) {
    return;
  }

  currentProfile = data;
  profileUsername.textContent = data.username || "Нет данных";
  profileEmail.textContent = data.email || "Нет данных";
  profileBalance.textContent = `${data.balance ?? "0.00"}`;
  profileAuthId.textContent = data.auth_user_id ?? data.id ?? "Нет данных";
}

function setEditMode(isEditing) {
  const profileGrid = document.querySelector(".profile-grid");

  profileGrid?.classList.toggle("is-hidden", isEditing);
  profileEditButton?.classList.toggle("is-hidden", isEditing);
  profileEditForm?.classList.toggle("is-hidden", !isEditing);

  if (isEditing && currentProfile && profileEditForm) {
    profileEditForm.elements.username.value = currentProfile.username || "";
    profileEditForm.elements.email.value = currentProfile.email || "";
    profileEditForm.elements.username.focus();
  }
}

function setProfileStatus(text, type = "is-success") {
  if (!profileStatus) {
    return;
  }

  profileStatus.classList.remove("is-error", "is-success");
  profileStatus.textContent = text;
  profileStatus.classList.add(type);
}

function clearSessionAndRedirect() {
  localStorage.removeItem("bingo_access_token");
  localStorage.removeItem("bingo_user");
  window.location.href = LOGIN_PAGE_URL;
}

async function loadProfile() {
  const token = localStorage.getItem("bingo_access_token");

  if (!token) {
    clearSessionAndRedirect();
    return;
  }

  renderProfile(readCachedUser());

  try {
    const response = await fetch(`${USER_API_URL}/users/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось загрузить профиль.");
    }

    renderProfile(data);
    localStorage.setItem("bingo_user", JSON.stringify(data));
    setProfileStatus("Профиль загружен.");
  } catch (error) {
    setProfileStatus(error.message, "is-error");
  }
}

async function updateProfile(event) {
  event.preventDefault();

  const token = localStorage.getItem("bingo_access_token");

  if (!token) {
    clearSessionAndRedirect();
    return;
  }

  const formData = new FormData(profileEditForm);
  const username = String(formData.get("username") || "").trim();
  const email = String(formData.get("email") || "").trim();

  if (!username || !email) {
    setProfileStatus("Введите username и email.", "is-error");
    return;
  }

  const submitButton = profileEditForm.querySelector("button[type='submit']");
  submitButton.disabled = true;
  setProfileStatus("Сохраняем профиль...");

  try {
    const response = await fetch(`${USER_API_URL}/users/me`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, email }),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось обновить профиль.");
    }

    renderProfile(data);
    localStorage.setItem("bingo_user", JSON.stringify(data));
    setEditMode(false);
    setProfileStatus("Профиль обновлен.");
  } catch (error) {
    setProfileStatus(error.message, "is-error");
  } finally {
    submitButton.disabled = false;
  }
}

if (logoutButton) {
  logoutButton.addEventListener("click", clearSessionAndRedirect);
}

if (profileEditButton) {
  profileEditButton.addEventListener("click", () => setEditMode(true));
}

if (profileCancelButton) {
  profileCancelButton.addEventListener("click", () => {
    setEditMode(false);
    setProfileStatus("Редактирование отменено.");
  });
}

if (profileEditForm) {
  profileEditForm.addEventListener("submit", updateProfile);
}

loadProfile();
