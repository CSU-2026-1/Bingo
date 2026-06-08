const SHOP_API_URL = "";
const LOGIN_PAGE_URL = "./login.html";

const shopStatus = document.querySelector("#shopStatus");
const shopBalance = document.querySelector("#shopBalance");
const shopCatalog = document.querySelector("#shopCatalog");
const shopResult = document.querySelector("#shopResult");
const shopResultCard = document.querySelector("#shopResultCard");
const shopResultClose = document.querySelector("#shopResultClose");

let currentBalance = 0;

const RARITY_STYLES = {
  common: { border: "rgba(202, 190, 214, 0.5)", glow: "rgba(202, 190, 214, 0.2)", label: "Обычная" },
  rare: { border: "rgba(78, 153, 255, 0.6)", glow: "rgba(78, 153, 255, 0.3)", label: "Редкая" },
  epic: { border: "rgba(138, 77, 255, 0.7)", glow: "rgba(138, 77, 255, 0.4)", label: "Эпическая" },
  legendary: { border: "rgba(255, 184, 77, 0.8)", glow: "rgba(255, 184, 77, 0.5)", label: "Легендарная" },
  woman: { border: "rgba(255, 93, 189, 0.9)", glow: "rgba(255, 93, 189, 0.5)", label: "ЖЕНЩИНА" },
};

function clearSessionAndRedirect() {
  localStorage.removeItem("bingo_access_token");
  localStorage.removeItem("bingo_user");
  window.location.href = LOGIN_PAGE_URL;
}

function setShopStatus(text, type = "is-success") {
  if (!shopStatus) return;
  shopStatus.classList.remove("is-error", "is-success");
  shopStatus.textContent = text;
  shopStatus.classList.add(type);
}

function updateBalanceDisplay(balance) {
  currentBalance = balance;
  if (shopBalance) {
    shopBalance.textContent = balance;
  }
}

function renderCatalog(items) {
  if (!shopCatalog) return;
  shopCatalog.innerHTML = "";

  items.forEach((item) => {
    const style = RARITY_STYLES[item.rarity] || RARITY_STYLES.common;
    const card = document.createElement("div");
    card.className = "shop-item";
    card.style.borderColor = style.border;
    card.style.boxShadow = `0 0 18px ${style.glow}`;
    card.innerHTML = `
      <div class="shop-item-rarity" style="color: ${style.border}">${item.label}</div>
      <div class="shop-item-price">${item.price} монет</div>
      <button class="auth-button shop-item-button" data-rarity="${item.rarity}" data-price="${item.price}">
        <span>Купить</span>
      </button>
    `;
    shopCatalog.appendChild(card);
  });

  shopCatalog.querySelectorAll(".shop-item-button").forEach((btn) => {
    btn.addEventListener("click", () => handlePurchase(btn.dataset.rarity, parseInt(btn.dataset.price)));
  });
}

function renderPurchasedCard(card) {
  if (!shopResultCard) return;
  const style = RARITY_STYLES[card.card_rarity] || RARITY_STYLES.common;
  const emoji = card.card_metadata?.emoji || "🎴";
  const colors = card.card_metadata?.colors || ["#8a4dff", "#00bfa5"];
  const imageHtml = card.image_url
    ? `<div class="purchased-card-image"><img src="${card.image_url}" alt="${card.card_name}" /></div>`
    : `<div class="purchased-card-emoji">${emoji}</div>`;

  shopResultCard.innerHTML = `
    <div class="purchased-card" style="border-color: ${style.border}; box-shadow: 0 0 24px ${style.glow}">
      ${imageHtml}
      <div class="purchased-card-name">${card.card_name}</div>
      <div class="purchased-card-rarity" style="color: ${style.border}">${style.label}</div>
      <div class="purchased-card-description">${card.card_description}</div>
      <div class="purchased-card-theme">Тема: ${card.card_theme}</div>
    </div>
  `;
}

async function handlePurchase(rarity, price) {
  const token = localStorage.getItem("bingo_access_token");
  if (!token) {
    clearSessionAndRedirect();
    return;
  }

  if (currentBalance < price) {
    setShopStatus("Недостаточно монет для покупки.", "is-error");
    return;
  }

  const buttons = shopCatalog?.querySelectorAll(".shop-item-button");
  buttons?.forEach((btn) => (btn.disabled = true));

  setShopStatus("Генерируем карточку и изображение... (может занять до 40 сек)");

  try {
    const response = await fetch(`${SHOP_API_URL}/shop/purchase`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ rarity }),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось купить карточку.");
    }

    updateBalanceDisplay(data.new_balance);
    renderPurchasedCard(data.card);
    shopResult?.classList.remove("is-hidden");
    setShopStatus("Карточка куплена!");

    const userData = JSON.parse(localStorage.getItem("bingo_user") || "{}");
    userData.balance = data.new_balance;
    localStorage.setItem("bingo_user", JSON.stringify(userData));
  } catch (error) {
    setShopStatus(error.message, "is-error");
  } finally {
    buttons?.forEach((btn) => (btn.disabled = false));
  }
}

async function loadCatalog() {
  const token = localStorage.getItem("bingo_access_token");
  if (!token) {
    clearSessionAndRedirect();
    return;
  }

  try {
    const [catalogRes, profileRes] = await Promise.all([
      fetch(`${SHOP_API_URL}/shop/catalog`),
      fetch(`${SHOP_API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    ]);

    if (!profileRes.ok) {
      throw new Error("Не удалось загрузить профиль.");
    }

    const profile = await profileRes.json();
    updateBalanceDisplay(profile.balance);

    if (!catalogRes.ok) {
      throw new Error("Не удалось загрузить каталог.");
    }

    const catalog = await catalogRes.json();
    renderCatalog(catalog);
    setShopStatus("Выберите карточку для покупки.");
  } catch (error) {
    setShopStatus(error.message, "is-error");
  }
}

if (shopResultClose) {
  shopResultClose.addEventListener("click", () => {
    shopResult?.classList.add("is-hidden");
  });
}

loadCatalog();
