const CARD_API_URL = "";
const GAME_ENGINE_API_URL = "";
const LOBBY_API_URL = "";
const WINNER_API_URL = "";
const LOBBY_PAGE_URL = "./lobby.html";
const LOGIN_PAGE_URL = "./login.html";

const gameIdValue = document.querySelector("#gameIdValue");
const cardActionButton = document.querySelector("#cardActionButton");
const claimBingoButton = document.querySelector("#claimBingoButton");
const gameStatusValue = document.querySelector("#gameStatusValue");
const lastBallValue = document.querySelector("#lastBallValue");
const drawnCountValue = document.querySelector("#drawnCountValue");
const gameMessage = document.querySelector("#gameMessage");
const bingoCard = document.querySelector("#bingoCard");
const cardOwner = document.querySelector("#cardOwner");
const markedCounter = document.querySelector("#markedCounter");
const winnerLine = document.querySelector("#winnerLine");
const winnerValue = document.querySelector("#winnerValue");
const comboList = document.querySelector("#comboList");
const roomProgressList = document.querySelector("#roomProgressList");

let currentCard = null;
let currentRoom = null;
let currentGameId = resolveGameId();
let lastBallNumber = null;
let currentDrawnNumbers = new Set();
let busy = false;
let autoRefreshTimer = null;
let countdownTimer = null;
let autoDrawTimer = null;
let countdownActive = false;
let ballFlowStarted = false;
let autoDrawBusy = false;
let claimPollTimer = null;
let claimPending = false;
let currentWinner = null;

const WINNING_PATTERNS = {
  top_row: { label: "Верхняя строка", cells: [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]] },
  middle_row: { label: "Средняя строка", cells: [[2, 0], [2, 1], [2, 2], [2, 3], [2, 4]] },
  bottom_row: { label: "Нижняя строка", cells: [[4, 0], [4, 1], [4, 2], [4, 3], [4, 4]] },
  left_column: { label: "Левый столбец", cells: [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]] },
  middle_column: { label: "Средний столбец", cells: [[0, 2], [1, 2], [2, 2], [3, 2], [4, 2]] },
  right_column: { label: "Правый столбец", cells: [[0, 4], [1, 4], [2, 4], [3, 4], [4, 4]] },
  main_diagonal: { label: "Диагональ", cells: [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4]] },
  anti_diagonal: { label: "Обратная диагональ", cells: [[0, 4], [1, 3], [2, 2], [3, 1], [4, 0]] },
  four_corners: { label: "Углы", cells: [[0, 0], [0, 4], [4, 0], [4, 4]] },
  x_shape: { label: "Крест X", cells: [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4], [0, 4], [1, 3], [3, 1], [4, 0]] },
  plus_shape: { label: "Плюс", cells: [[0, 2], [1, 2], [2, 0], [2, 1], [2, 2], [2, 3], [2, 4], [3, 2], [4, 2]] },
  small_frame: { label: "Малая рамка", cells: [[1, 1], [1, 2], [1, 3], [2, 1], [2, 3], [3, 1], [3, 2], [3, 3]] },
};

function getToken() {
  return localStorage.getItem("bingo_access_token");
}

function clearAuthSession() {
  localStorage.removeItem("bingo_access_token");
  localStorage.removeItem("bingo_user");
}

function readCachedUser() {
  try {
    return JSON.parse(localStorage.getItem("bingo_user") || "null");
  } catch {
    return null;
  }
}

function decodeTokenPayload() {
  const token = getToken();
  if (!token) {
    return null;
  }

  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

function getCurrentUserId() {
  const payload = decodeTokenPayload();
  return payload?.sub ? String(payload.sub) : "";
}

function getCurrentDisplayName() {
  return readCachedUser()?.username || decodeTokenPayload()?.username || getCurrentUserId();
}

function setGameMessage(text, type = "is-success") {
  gameMessage.classList.remove("is-error", "is-success");
  gameMessage.textContent = text;
  gameMessage.classList.add(type);
}

function isNumericId(value) {
  return /^[1-9]\d*$/.test(String(value || "").trim());
}

function resolveGameId() {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get("game_id");
  const fromStorage = localStorage.getItem("bingo_game_id");
  const gameId = String(fromUrl || fromStorage || "").trim();
  return isNumericId(gameId) ? gameId : "";
}

function renderGameId() {
  gameIdValue.textContent = currentGameId || "Не выбрана";
}

function getGameId() {
  if (!currentGameId) {
    throw new Error("Сначала создайте комнату в лобби.");
  }
  return currentGameId;
}

function getAuthHeaders() {
  const token = getToken();
  if (!token) {
    throw new Error("Нужно войти в аккаунт.");
  }
  const headers = { Authorization: `Bearer ${token}` };
  const username = readCachedUser()?.username;
  if (username) {
    headers["X-User-Name"] = username;
  }
  return headers;
}

async function readResponse(response, fallbackMessage) {
  const data = await response.json().catch(() => ({}));

  if (response.status === 401) {
    clearAuthSession();
    throw new Error("Сессия истекла. Войдите заново.");
  }

  if (!response.ok) {
    throw new Error(data.detail || fallbackMessage);
  }

  return data;
}

async function loadRoom() {
  const gameId = getGameId();
  const response = await fetch(`${LOBBY_API_URL}/rooms/${encodeURIComponent(gameId)}`);
  return readResponse(response, "Не удалось загрузить комнату.");
}

async function createCard() {
  const gameId = getGameId();
  const response = await fetch(`${CARD_API_URL}/games/${encodeURIComponent(gameId)}/cards/me`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return readResponse(response, "Не удалось создать карточку.");
}

async function loadCard() {
  const gameId = getGameId();
  const response = await fetch(`${CARD_API_URL}/games/${encodeURIComponent(gameId)}/cards/me`, {
    headers: getAuthHeaders(),
  });
  return readResponse(response, "Карточка не найдена.");
}

async function markNumber(number) {
  const gameId = getGameId();
  const response = await fetch(`${CARD_API_URL}/games/${encodeURIComponent(gameId)}/cards/me/marks`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ number }),
  });
  return readResponse(response, "Не удалось отметить шар.");
}

async function loadGameState() {
  const gameId = getGameId();
  const response = await fetch(`${GAME_ENGINE_API_URL}/game/${encodeURIComponent(gameId)}/state`);
  return readResponse(response, "Игра еще не запущена.");
}

async function drawBall() {
  const gameId = getGameId();
  const response = await fetch(`${LOBBY_API_URL}/rooms/${encodeURIComponent(gameId)}/draw`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return readResponse(response, "Не удалось достать шар.");
}

async function submitWinnerClaim() {
  const gameId = getGameId();
  const response = await fetch(`${WINNER_API_URL}/games/${encodeURIComponent(gameId)}/winner-claims`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return readResponse(response, "Не удалось отправить заявку BINGO.");
}

async function loadWinnerClaim(claimId) {
  const gameId = getGameId();
  const response = await fetch(
    `${WINNER_API_URL}/games/${encodeURIComponent(gameId)}/winner-claims/${encodeURIComponent(claimId)}`,
    {
      headers: getAuthHeaders(),
    },
  );
  return readResponse(response, "Не удалось проверить заявку BINGO.");
}

async function loadWinner() {
  const gameId = getGameId();
  const response = await fetch(`${WINNER_API_URL}/games/${encodeURIComponent(gameId)}/winner`);

  if (response.status === 404) {
    return null;
  }

  return readResponse(response, "Не удалось загрузить победителя.");
}

async function loadRoomProgress(room) {
  const response = await fetch(`${CARD_API_URL}/games/${encodeURIComponent(room.id)}/cards/progress`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_ids: (room.players || []).map((player) => String(player.user_id)),
      winning_pattern: room.winning_pattern || "top_row",
    }),
  });
  return readResponse(response, "Не удалось загрузить прогресс игроков.");
}

function claimStatusMessage(claim) {
  return {
    queued: "Заявка отправлена. Ждем проверку...",
    processing: "Проверяем карточку...",
    won: "BINGO подтверждено. Вы победили.",
    rejected: "BINGO пока нет: нет закрытой линии.",
    verification_failed: "Не удалось проверить BINGO. Попробуйте еще раз.",
    reward_failed: "BINGO подтверждено, но награда не начислилась автоматически.",
  }[claim.status] || "Проверяем заявку BINGO...";
}

function isFinalClaimStatus(status) {
  return ["won", "rejected", "verification_failed", "reward_failed"].includes(status);
}

function claimMessageType(status) {
  return status === "won" || status === "reward_failed" ? "is-success" : "is-error";
}

function playerName(userId) {
  const player = currentRoom?.players?.find((roomPlayer) => roomPlayer.user_id === String(userId));
  return player?.display_name || `Игрок ${userId}`;
}

function isRoomFinished() {
  return currentRoom?.status === "finished";
}

function stopCountdown() {
  if (countdownTimer) {
    window.clearInterval(countdownTimer);
    countdownTimer = null;
  }
  countdownActive = false;
}

function stopAutoDraw() {
  if (autoDrawTimer) {
    window.clearInterval(autoDrawTimer);
    autoDrawTimer = null;
  }
  autoDrawBusy = false;
}

function stopBallFlow() {
  stopCountdown();
  stopAutoDraw();
  ballFlowStarted = false;
}

function renderWinner(winner) {
  currentWinner = winner;

  if (!winner) {
    winnerLine.classList.add("is-hidden");
    winnerValue.textContent = "...";
    return;
  }

  winnerLine.classList.remove("is-hidden");
  winnerValue.textContent = playerName(winner.user_id);
}

function renderRoomProgress(progressItems = []) {
  roomProgressList.replaceChildren();

  const players = currentRoom?.players || [];
  if (!players.length) {
    const empty = document.createElement("div");
    empty.className = "room-progress-empty";
    empty.textContent = "В комнате пока нет игроков";
    roomProgressList.appendChild(empty);
    return;
  }

  const progressByUserId = new Map(progressItems.map((item) => [String(item.user_id), item]));
  players.forEach((player) => {
    const progress = progressByUserId.get(String(player.user_id));
    const item = document.createElement("div");
    item.className = "room-progress-item";
    if (progress?.is_complete) {
      item.classList.add("is-complete");
    }

    const name = document.createElement("span");
    name.className = "room-progress-name";
    name.textContent = player.display_name || `Игрок ${player.user_id}`;

    const value = document.createElement("strong");
    value.className = "room-progress-value";
    value.textContent = progress?.has_card ? `${progress.progress}/${progress.total}` : "нет карты";

    item.append(name, value);
    roomProgressList.appendChild(item);
  });
}

function renderRoomState(room) {
  currentRoom = room;
  renderRoomProgress();
  renderHostControls();
  if (currentCard) {
    renderCombinations(currentCard);
    updateCardAvailability();
  }

  if (isRoomFinished()) {
    stopBallFlow();
    gameStatusValue.textContent = "Завершена";
    gameStatusValue.classList.remove("is-active");
    gameStatusValue.classList.add("is-finished");
    claimBingoButton.disabled = true;
    return;
  }

  gameStatusValue.classList.remove("is-finished");
}

function stopClaimPolling() {
  if (claimPollTimer) {
    window.clearInterval(claimPollTimer);
    claimPollTimer = null;
  }
  claimPending = false;
}

function startClaimPolling(claimId) {
  stopClaimPolling();

  let attempts = 0;
  claimPending = true;
  claimBingoButton.disabled = true;
  setGameMessage("Заявка отправлена. Ждем проверку...");

  claimPollTimer = window.setInterval(async () => {
    attempts += 1;

    try {
      const claim = await loadWinnerClaim(claimId);
      const message = claimStatusMessage(claim);

      if (isFinalClaimStatus(claim.status)) {
        stopClaimPolling();
        claimBingoButton.disabled = false;
        setGameMessage(message, claimMessageType(claim.status));
        await refreshRoomState().catch(() => {});
        await refreshGameState().catch(() => {});
        return;
      }

      setGameMessage(message);
    } catch (error) {
      stopClaimPolling();
      claimBingoButton.disabled = false;
      setGameMessage(error.message, "is-error");
      return;
    }

    if (attempts >= 20) {
      stopClaimPolling();
      claimBingoButton.disabled = false;
      setGameMessage("Заявка все еще проверяется. Попробуйте обновить страницу через несколько секунд.");
    }
  }, 1000);
}

function isHost() {
  return currentRoom?.host_user_id && currentRoom.host_user_id === getCurrentUserId();
}

function renderHostControls() {
  return;
}

function lineProgress(cells) {
  return cells.filter((cell) => cell.is_free || cell.marked).length;
}

function patternCellKey(row, col) {
  return `${row}:${col}`;
}

function selectedPattern() {
  return WINNING_PATTERNS[currentRoom?.winning_pattern] || WINNING_PATTERNS.top_row;
}

function selectedPatternCells() {
  return new Set(selectedPattern().cells.map(([row, col]) => patternCellKey(row, col)));
}

function renderCombinations(card) {
  comboList.replaceChildren();

  if (!card) {
    const empty = document.createElement("span");
    empty.textContent = "Откройте карточку";
    comboList.appendChild(empty);
    return;
  }

  const pattern = selectedPattern();
  const cells = pattern.cells.map(([row, col]) => card.cells[row][col]);
  const progress = lineProgress(cells);
  const item = document.createElement("span");
  item.className = "combo-item";
  item.textContent = `${pattern.label}: ${progress}/${cells.length}`;
  if (progress === cells.length) {
    item.classList.add("is-complete");
  }
  comboList.appendChild(item);
}

function updateCardAvailability() {
  bingoCard.querySelectorAll(".bingo-cell").forEach((button) => {
    button.disabled = button.classList.contains("is-free") || isRoomFinished();
  });
}

function renderCard(card) {
  currentCard = card;
  bingoCard.querySelectorAll(".bingo-cell").forEach((cell) => cell.remove());
  const patternCells = selectedPatternCells();

  card.cells.flat().forEach((cell) => {
    const button = document.createElement("button");
    button.className = "bingo-cell";
    button.type = "button";
    button.disabled = cell.is_free || isRoomFinished();
    button.dataset.number = cell.number || "";
    button.setAttribute("aria-label", cell.is_free ? "FREE" : `${cell.number}`);

    if (cell.marked) {
      button.classList.add("is-marked");
    }
    if (cell.is_free) {
      button.classList.add("is-free");
    }
    if (patternCells.has(patternCellKey(cell.row, cell.col))) {
      button.classList.add("is-pattern");
    }

    const label = document.createElement("strong");
    label.textContent = cell.is_free ? "FREE" : cell.number;

    button.addEventListener("click", () => run(async () => {
      if (cell.is_free || !cell.number) {
        return;
      }
      if (button.classList.contains("is-marked")) {
        setGameMessage("Этот номер уже отмечен.");
        return;
      }
      if (!currentDrawnNumbers.has(cell.number)) {
        setGameMessage("Этот номер еще не выпадал.", "is-error");
        return;
      }

      const result = await markNumber(cell.number);
      renderCard(result.card);
      await refreshRoomState().catch(() => {});
      setGameMessage(result.matched ? `Отмечено: ${cell.number}.` : "Такого номера нет в карточке.");
    }));

    button.appendChild(label);
    bingoCard.appendChild(button);
  });

  const marked = card.cells.flat().filter((cell) => cell.marked).length;
  cardOwner.textContent = getCurrentDisplayName() || `Игрок ${card.user_id}`;
  markedCounter.textContent = `${marked} отмечено`;
  cardActionButton.classList.add("is-hidden");
  claimBingoButton.disabled = busy || claimPending || isRoomFinished();
  renderCombinations(card);
  updateCardAvailability();
}

function renderGameState(state) {
  lastBallNumber = state.last_ball?.number || null;
  currentDrawnNumbers = new Set((state.drawn_balls || []).map((ball) => ball.number).filter(Boolean));
  if (isRoomFinished()) {
    gameStatusValue.textContent = "Завершена";
    gameStatusValue.classList.remove("is-active");
    gameStatusValue.classList.add("is-finished");
  } else {
    gameStatusValue.textContent = state.is_active ? "Игра идет" : "Ожидание";
    gameStatusValue.classList.toggle("is-active", Boolean(state.is_active));
    gameStatusValue.classList.remove("is-finished");
  }

  if (countdownActive) {
    claimBingoButton.disabled = true;
    updateCardAvailability();
    return;
  }

  lastBallValue.textContent = state.last_ball?.number || "...";
  drawnCountValue.textContent = `${state.drawn_count || 0} из 75`;
  claimBingoButton.disabled = busy || claimPending || !currentCard || isRoomFinished();
  updateCardAvailability();
  startBallFlow(state);
}

function setBusy(isBusy) {
  busy = isBusy;
  cardActionButton.disabled = isBusy;
  claimBingoButton.disabled = isBusy || claimPending || !currentCard || isRoomFinished();
  updateCardAvailability();
}

async function run(action) {
  if (busy) {
    return;
  }

  setBusy(true);
  try {
    await action();
  } catch (error) {
    setGameMessage(error.message, "is-error");
    if (error.message.includes("войти") || error.message.includes("Сессия")) {
      setTimeout(() => {
        window.location.href = LOGIN_PAGE_URL;
      }, 650);
    }
  } finally {
    setBusy(false);
  }
}

async function openOrCreateCard() {
  try {
    setGameMessage("Открываем карточку...");
    renderCard(await loadCard());
    await refreshRoomState().catch(() => {});
    setGameMessage(isHost() ? "Карточка готова. Вы достаете шары для комнаты." : "Карточка готова. Ждем шар от хоста.");
  } catch (error) {
    if (!String(error.message).toLowerCase().includes("card not found") && !String(error.message).includes("Карточка")) {
      throw error;
    }

    setGameMessage("Создаем карточку...");
    renderCard(await createCard());
    await refreshRoomState().catch(() => {});
    setGameMessage(isHost() ? "Карточка создана. Вы достаете шары для комнаты." : "Карточка создана. Ждем шар от хоста.");
  }
}

async function refreshGameState() {
  const state = await loadGameState();
  renderGameState(state);
  return state;
}

async function refreshRoomState() {
  const room = await loadRoom();
  renderRoomState(room);
  loadRoomProgress(room)
    .then(renderRoomProgress)
    .catch(() => {});

  if (room.status === "finished") {
    const winner = await loadWinner().catch(() => null);
    renderWinner(winner);
    setGameMessage(
      winner ? `Игра завершена. Победитель: ${playerName(winner.user_id)}.` : "Игра завершена.",
      "is-success",
    );
  }

  return room;
}

async function autoDrawNextBall() {
  if (!isHost() || isRoomFinished() || autoDrawBusy) {
    return;
  }

  autoDrawBusy = true;
  try {
    const ball = await drawBall();
    await refreshRoomState().catch(() => {});
    await refreshGameState();
    setGameMessage(`Выпал шар ${ball.number}.`);
  } catch (error) {
    stopAutoDraw();
    if (!String(error.message).includes("Only active room")) {
      setGameMessage(error.message, "is-error");
    }
  } finally {
    autoDrawBusy = false;
  }
}

function startAutoDraw() {
  if (!isHost() || autoDrawTimer || isRoomFinished()) {
    return;
  }

  autoDrawNextBall();
  autoDrawTimer = window.setInterval(autoDrawNextBall, 4000);
}

function startCountdownThenDraw() {
  if (countdownTimer || countdownActive || isRoomFinished()) {
    return;
  }

  let secondsLeft = 5;
  countdownActive = true;
  gameStatusValue.textContent = "Старт";
  gameStatusValue.classList.add("is-active");
  lastBallValue.textContent = secondsLeft;
  drawnCountValue.textContent = "До первого шара";
  claimBingoButton.disabled = true;

  countdownTimer = window.setInterval(() => {
    secondsLeft -= 1;

    if (secondsLeft > 0) {
      lastBallValue.textContent = secondsLeft;
      return;
    }

    stopCountdown();
    lastBallValue.textContent = "...";
    drawnCountValue.textContent = "0 из 75";
    setGameMessage(isHost() ? "Автоматически достаем шары каждые 4 секунды." : "Шары появляются автоматически.");
    startAutoDraw();
  }, 1000);
}

function startBallFlow(state) {
  if (ballFlowStarted || isRoomFinished() || !state.is_active) {
    return;
  }

  ballFlowStarted = true;

  if ((state.drawn_count || 0) > 0) {
    startAutoDraw();
    return;
  }

  startCountdownThenDraw();
}

function startAutoRefresh() {
  if (autoRefreshTimer || !currentGameId) {
    return;
  }

  autoRefreshTimer = window.setInterval(() => {
    refreshRoomState().catch(() => {});
    refreshGameState().catch(() => {
      gameStatusValue.textContent = "Ожидание";
      gameStatusValue.classList.remove("is-active");
    });
  }, 2000);
}

cardActionButton.addEventListener("click", () => run(async () => {
  await openOrCreateCard();
  await refreshGameState().catch(() => {});
}));

claimBingoButton.addEventListener("click", () => run(async () => {
  if (!currentCard) {
    throw new Error("Сначала откройте карточку.");
  }

  const claim = await submitWinnerClaim();
  startClaimPolling(claim.claim_id);
}));

renderGameId();

if (!getToken()) {
  setGameMessage("Нужно войти в аккаунт.", "is-error");
  setTimeout(() => {
    window.location.href = LOGIN_PAGE_URL;
  }, 650);
} else if (!currentGameId) {
  setGameMessage("Сначала откройте лобби и выберите комнату.", "is-error");
  setTimeout(() => {
    window.location.href = LOBBY_PAGE_URL;
  }, 900);
} else {
  localStorage.setItem("bingo_game_id", currentGameId);
  run(async () => {
    await refreshRoomState();
    await openOrCreateCard();
    await refreshGameState().catch(() => {
      setGameMessage(isHost() ? "Запустите игру в комнате, затем доставайте шары." : "Карточка готова. Ждем запуска игры.");
    });
    startAutoRefresh();
  });
}
