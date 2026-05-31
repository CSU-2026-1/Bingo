const LOBBY_API_URL = "";
const LOGIN_PAGE_URL = "./login.html";
const GAME_PAGE_URL = "./game.html";
const LOBBY_PAGE_URL = "./lobby.html";

const createRoomButton = document.querySelector("#createRoomButton");
const roomSettingsForm = document.querySelector("#roomSettingsForm");
const roomNameInput = document.querySelector("#roomNameInput");
const cancelCreateRoomButton = document.querySelector("#cancelCreateRoomButton");
const startRoomButton = document.querySelector("#startRoomButton");
const lobbyMessage = document.querySelector("#lobbyMessage");
const roomStatus = document.querySelector("#roomStatus");
const roomIdValue = document.querySelector("#roomIdValue");
const roomLinkValue = document.querySelector("#roomLinkValue");
const roomHostValue = document.querySelector("#roomHostValue");
const playerList = document.querySelector("#playerList");
const patternOptions = document.querySelector("#patternOptions");
const patternModal = document.querySelector("#patternModal");
const openPatternModalButton = document.querySelector("#openPatternModalButton");
const closePatternModalButton = document.querySelector("#closePatternModalButton");
const selectedPatternPreview = document.querySelector("#selectedPatternPreview");
const selectedPatternLabel = document.querySelector("#selectedPatternLabel");
const roomBrowser = document.querySelector("#roomBrowser");
const currentRoomView = document.querySelector("#currentRoomView");
const availableRoomList = document.querySelector("#availableRoomList");
const roomSearchInput = document.querySelector("#roomSearchInput");
const refreshRoomsButton = document.querySelector("#refreshRoomsButton");
const roomBrowserMessage = document.querySelector("#roomBrowserMessage");
const closeRoomButton = document.querySelector("#closeRoomButton");

let currentRoom = null;
let availableRooms = [];
let busy = false;
let selectedWinningPattern = "top_row";
let roomPollTimer = null;

const WINNING_PATTERNS = [
  { id: "top_row", label: "Верхняя строка", cells: [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]] },
  { id: "middle_row", label: "Средняя строка", cells: [[2, 0], [2, 1], [2, 2], [2, 3], [2, 4]] },
  { id: "bottom_row", label: "Нижняя строка", cells: [[4, 0], [4, 1], [4, 2], [4, 3], [4, 4]] },
  { id: "left_column", label: "Левый столбец", cells: [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]] },
  { id: "middle_column", label: "Средний столбец", cells: [[0, 2], [1, 2], [2, 2], [3, 2], [4, 2]] },
  { id: "right_column", label: "Правый столбец", cells: [[0, 4], [1, 4], [2, 4], [3, 4], [4, 4]] },
  { id: "main_diagonal", label: "Диагональ", cells: [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4]] },
  { id: "anti_diagonal", label: "Обратная диагональ", cells: [[0, 4], [1, 3], [2, 2], [3, 1], [4, 0]] },
  { id: "four_corners", label: "Углы", cells: [[0, 0], [0, 4], [4, 0], [4, 4]] },
  { id: "x_shape", label: "Крест X", cells: [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4], [0, 4], [1, 3], [3, 1], [4, 0]] },
  { id: "plus_shape", label: "Плюс", cells: [[0, 2], [1, 2], [2, 0], [2, 1], [2, 2], [2, 3], [2, 4], [3, 2], [4, 2]] },
  { id: "small_frame", label: "Малая рамка", cells: [[1, 1], [1, 2], [1, 3], [2, 1], [2, 3], [3, 1], [3, 2], [3, 3]] },
];

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

function isHost() {
  return currentRoom?.host_user_id && currentRoom.host_user_id === getCurrentUserId();
}

function setLobbyMessage(text, type = "is-success") {
  lobbyMessage.classList.remove("is-error", "is-success");
  lobbyMessage.textContent = text;
  lobbyMessage.classList.add(type);
}

function setBrowserMessage(text, type = "") {
  roomBrowserMessage.classList.remove("is-error", "is-success");
  roomBrowserMessage.textContent = text;
  if (type) {
    roomBrowserMessage.classList.add(type);
  }
}

function isNumericId(value) {
  return /^[1-9]\d*$/.test(String(value || "").trim());
}

function statusLabel(status) {
  return {
    waiting: "Ожидание игроков",
    active: "Игра идет",
    finished: "Завершена",
  }[status] || status || "Неизвестно";
}

function patternLabel(patternId) {
  return WINNING_PATTERNS.find((pattern) => pattern.id === patternId)?.label || patternId;
}

function getAuthHeaders() {
  const token = getToken();
  if (!token) {
    throw new Error("Нужно войти в аккаунт.");
  }

  const headers = { Authorization: `Bearer ${token}` };
  const cachedUser = readCachedUser();
  if (cachedUser?.username) {
    headers["X-User-Name"] = cachedUser.username;
  }
  return headers;
}

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));

  if (response.status === 401) {
    clearAuthSession();
    throw new Error("Сессия истекла. Войдите заново.");
  }

  if (!response.ok) {
    throw new Error(data.detail || "Сервис комнат вернул ошибку.");
  }

  return data;
}

function stopRoomPolling() {
  if (roomPollTimer) {
    clearInterval(roomPollTimer);
    roomPollTimer = null;
  }
}

function startRoomPolling() {
  stopRoomPolling();
  roomPollTimer = setInterval(checkCurrentRoom, 4000);
}

async function createRoom(payload) {
  const response = await fetch(`${LOBBY_API_URL}/rooms`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return readResponse(response);
}

async function listWaitingRooms() {
  const response = await fetch(`${LOBBY_API_URL}/rooms?status_filter=waiting`);
  return readResponse(response);
}

async function joinRoom(roomId) {
  const response = await fetch(`${LOBBY_API_URL}/rooms/${encodeURIComponent(roomId)}/join`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return readResponse(response);
}

async function loadRoom(roomId) {
  const response = await fetch(`${LOBBY_API_URL}/rooms/${encodeURIComponent(roomId)}`);
  return readResponse(response);
}

async function deleteRoom(roomId) {
  const response = await fetch(`${LOBBY_API_URL}/rooms/${encodeURIComponent(roomId)}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (response.status === 204) {
    return;
  }

  await readResponse(response);
}

async function startRoom(roomId) {
  const response = await fetch(`${LOBBY_API_URL}/rooms/${encodeURIComponent(roomId)}/start`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ winning_pattern: selectedWinningPattern }),
  });
  return readResponse(response);
}

function gameUrl(roomId) {
  return `${GAME_PAGE_URL}?game_id=${encodeURIComponent(roomId)}`;
}

function goToGame(roomId) {
  localStorage.setItem("bingo_game_id", String(roomId));
  window.location.href = gameUrl(roomId);
}

function lobbyRoomUrl(roomId) {
  return `${window.location.origin}${window.location.pathname}?room_id=${encodeURIComponent(roomId)}`;
}

function showCreateSettings() {
  roomSettingsForm.classList.remove("is-hidden");
  createRoomButton.classList.add("is-hidden");
  roomNameInput.focus();
  renderSelectedPattern();
  renderPatternOptions();
}

function hideCreateSettings() {
  roomSettingsForm.classList.add("is-hidden");
  createRoomButton.classList.remove("is-hidden");
}

function renderEmptyRoom() {
  currentRoom = null;
  stopRoomPolling();
  localStorage.removeItem("bingo_game_id");
  createRoomButton.classList.remove("is-hidden");
  roomBrowser.classList.remove("is-hidden");
  currentRoomView.classList.add("is-hidden");
  startRoomButton.disabled = true;
  closeRoomButton.classList.add("is-hidden");
  closeRoomButton.disabled = true;
  renderSelectedPattern();
  renderPatternOptions();
}

function syncRoom(room) {
  currentRoom = room;
  selectedWinningPattern = room.winning_pattern || selectedWinningPattern;
  localStorage.setItem("bingo_game_id", String(room.id));
  renderRoom(room);
}

function renderRoom(room) {
  roomBrowser.classList.add("is-hidden");
  currentRoomView.classList.remove("is-hidden");
  hideCreateSettings();
  createRoomButton.classList.add("is-hidden");

  roomStatus.textContent = `${room.name || "BINGO room"} · ${statusLabel(room.status)} · ${patternLabel(room.winning_pattern)}`;
  roomIdValue.textContent = room.id;
  roomLinkValue.href = lobbyRoomUrl(room.id);
  roomLinkValue.textContent = lobbyRoomUrl(room.id);

  const host = room.players.find((player) => player.user_id === room.host_user_id);
  roomHostValue.textContent = `Хост: ${host?.display_name || room.host_user_id}`;

  playerList.replaceChildren();
  room.players.forEach((player) => {
    const item = document.createElement("div");
    item.className = "lobby-player";

    const name = document.createElement("strong");
    name.textContent = player.display_name || `Игрок ${player.user_id}`;

    const joinedAt = document.createElement("span");
    joinedAt.textContent = new Date(player.joined_at).toLocaleString("ru-RU");

    item.append(name, joinedAt);
    playerList.appendChild(item);
  });

  startRoomButton.disabled = busy || room.status !== "waiting" || !isHost();
  closeRoomButton.classList.toggle("is-hidden", !isHost() || room.status !== "waiting");
  closeRoomButton.disabled = busy || !isHost() || room.status !== "waiting";
  renderPatternOptions();
  renderSelectedPattern();
  startRoomPolling();
}

function renderAvailableRooms() {
  const search = roomSearchInput.value.trim();
  const rooms = search
    ? availableRooms.filter((room) => String(room.id).includes(search))
    : availableRooms;

  availableRoomList.replaceChildren();

  if (!rooms.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = search ? "Комната с таким кодом не найдена." : "Пока нет комнат в ожидании.";
    availableRoomList.appendChild(empty);
    return;
  }

  rooms.forEach((room) => {
    const item = document.createElement("article");
    item.className = "available-room";

    const info = document.createElement("div");
    info.className = "available-room-info";

    const title = document.createElement("strong");
    title.textContent = room.name || `Комната ${room.id}`;

    const meta = document.createElement("span");
    meta.textContent = `Код ${room.id} · ${room.players.length} игрок(ов) · ${patternLabel(room.winning_pattern)}`;

    info.append(title, meta);

    const joinButton = document.createElement("button");
    joinButton.className = "auth-button game-button available-room-join";
    joinButton.type = "button";
    joinButton.disabled = busy;
    joinButton.textContent = "Войти";
    joinButton.addEventListener("click", () => {
      withLobbyAction(async () => {
        setLobbyMessage("Входим в комнату...");
        syncRoom(await joinRoom(room.id));
        setLobbyMessage("Вы в комнате. Когда хост начнет игру, переходите к карточке.");
      });
    });

    item.append(info, joinButton);
    availableRoomList.appendChild(item);
  });
}

async function refreshRooms() {
  setBrowserMessage("Обновляем список комнат...");
  availableRooms = await listWaitingRooms();
  renderAvailableRooms();
  setBrowserMessage("Выберите комнату или создайте новую.", "is-success");
}

function setBusy(isBusy) {
  busy = isBusy;
  createRoomButton.disabled = isBusy;
  roomSettingsForm.querySelectorAll("input, button").forEach((element) => {
    element.disabled = isBusy;
  });
  refreshRoomsButton.disabled = isBusy;
  startRoomButton.disabled = isBusy || !currentRoom || currentRoom.status !== "waiting" || !isHost();
  closeRoomButton.disabled = isBusy || !currentRoom || currentRoom.status !== "waiting" || !isHost();
  openPatternModalButton.disabled = isBusy || currentRoom !== null;
  renderAvailableRooms();
  renderPatternOptions();
  renderSelectedPattern();
}

function patternCellKey(row, col) {
  return `${row}:${col}`;
}

function selectedPattern() {
  return WINNING_PATTERNS.find((pattern) => pattern.id === selectedWinningPattern) || WINNING_PATTERNS[0];
}

function renderPatternPreview(container, pattern) {
  container.replaceChildren();

  const selectedCells = new Set(pattern.cells.map(([row, col]) => patternCellKey(row, col)));
  for (let row = 0; row < 5; row += 1) {
    for (let col = 0; col < 5; col += 1) {
      const dot = document.createElement("span");
      dot.className = selectedCells.has(patternCellKey(row, col)) ? "pattern-dot is-selected" : "pattern-dot";
      container.appendChild(dot);
    }
  }
}

function renderSelectedPattern() {
  const pattern = selectedPattern();
  selectedPatternLabel.textContent = pattern.label;
  renderPatternPreview(selectedPatternPreview, pattern);
}

function renderPatternOptions() {
  patternOptions.replaceChildren();

  WINNING_PATTERNS.forEach((pattern) => {
    const option = document.createElement("button");
    option.className = "pattern-option";
    option.type = "button";
    option.disabled = busy || currentRoom !== null;
    option.setAttribute("aria-pressed", String(pattern.id === selectedWinningPattern));

    const preview = document.createElement("span");
    preview.className = "pattern-preview";
    renderPatternPreview(preview, pattern);

    const label = document.createElement("strong");
    label.textContent = pattern.label;

    option.append(preview, label);
    option.addEventListener("click", () => {
      selectedWinningPattern = pattern.id;
      closePatternModal();
      renderPatternOptions();
      renderSelectedPattern();
    });
    patternOptions.appendChild(option);
  });
}

function openPatternModal() {
  if (openPatternModalButton.disabled) {
    return;
  }
  patternModal.classList.remove("is-hidden");
}

function closePatternModal() {
  patternModal.classList.add("is-hidden");
}

async function withLobbyAction(action) {
  if (busy) {
    return;
  }

  setBusy(true);
  try {
    await action();
  } catch (error) {
    setLobbyMessage(error.message, "is-error");
    setBrowserMessage(error.message, "is-error");
    if (error.message.includes("войти") || error.message.includes("Сессия")) {
      setTimeout(() => {
        window.location.href = LOGIN_PAGE_URL;
      }, 650);
    }
  } finally {
    setBusy(false);
  }
}

async function checkCurrentRoom() {
  if (!currentRoom || busy) {
    return;
  }

  try {
    const room = await loadRoom(currentRoom.id);
    if (room.status === "active") {
      goToGame(room.id);
      return;
    }

    syncRoom(room);
  } catch (error) {
    if (String(error.message).includes("Room not found")) {
      renderEmptyRoom();
      await refreshRooms();
      setLobbyMessage("Комната закрыта. Вы вернулись к списку комнат.", "is-success");
      return;
    }

    setLobbyMessage(error.message, "is-error");
  }
}

createRoomButton.addEventListener("click", showCreateSettings);
cancelCreateRoomButton.addEventListener("click", hideCreateSettings);

roomSettingsForm.addEventListener("submit", (event) => {
  event.preventDefault();
  withLobbyAction(async () => {
    const name = roomNameInput.value.trim();
    if (!name) {
      throw new Error("Введите название комнаты.");
    }

    setLobbyMessage("Создаем комнату...");
    syncRoom(await createRoom({ name, winning_pattern: selectedWinningPattern }));
    setLobbyMessage("Комната создана. Передайте код или ссылку другим игрокам.");
  });
});

refreshRoomsButton.addEventListener("click", () => withLobbyAction(refreshRooms));
roomSearchInput.addEventListener("input", renderAvailableRooms);

startRoomButton.addEventListener("click", () => withLobbyAction(async () => {
  if (!currentRoom) {
    throw new Error("Сначала выберите комнату.");
  }

  setLobbyMessage("Запускаем игру...");
  const room = await startRoom(currentRoom.id);
  goToGame(room.id);
}));

closeRoomButton.addEventListener("click", () => withLobbyAction(async () => {
  if (!currentRoom) {
    throw new Error("Сначала выберите комнату.");
  }

  setLobbyMessage("Закрываем комнату...");
  await deleteRoom(currentRoom.id);
  renderEmptyRoom();
  await refreshRooms();
  setLobbyMessage("Комната закрыта.");
}));

openPatternModalButton.addEventListener("click", openPatternModal);
closePatternModalButton.addEventListener("click", closePatternModal);
patternModal.addEventListener("click", (event) => {
  if (event.target === patternModal) {
    closePatternModal();
  }
});

renderEmptyRoom();

const linkedRoomId = new URLSearchParams(window.location.search).get("room_id");
if (isNumericId(linkedRoomId)) {
  withLobbyAction(async () => {
    const room = await loadRoom(linkedRoomId);
    if (room.status === "waiting") {
      syncRoom(await joinRoom(linkedRoomId));
      setLobbyMessage("Вы вошли в комнату по ссылке.");
    } else {
      if (room.status === "active") {
        renderEmptyRoom();
        await refreshRooms();
        setLobbyMessage("Игра уже началась. Войти в эту комнату нельзя.", "is-error");
        return;
      }

      syncRoom(room);
      setLobbyMessage("Открыта комната по ссылке.");
    }
  });
} else {
  withLobbyAction(refreshRooms);
}
