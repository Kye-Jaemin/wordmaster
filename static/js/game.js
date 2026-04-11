/* ─── WordMaster — Game Logic ─────────────────────────────── */
"use strict";

// ─── State ────────────────────────────────────────────────────
let secretWord  = "";
let currentRow  = 0;
let currentCol  = 0;
let currentGuess = [];
let gameOver    = false;
let tiles       = [];
let hintUsed    = false;

const board      = document.getElementById("board");
const keyboard   = document.getElementById("keyboard");
const toastArea  = document.getElementById("toast-area");
const resultPanel= document.getElementById("result-panel");
const resultAd   = document.getElementById("result-ad");

// ─── Init ──────────────────────────────────────────────────────
async function init() {
  buildBoard();
  await fetchWord();
  addEventListeners();
}

function buildBoard() {
  board.innerHTML = "";
  tiles = [];
  for (let r = 0; r < MAX_GUESSES; r++) {
    const rowTiles = [];
    for (let c = 0; c < WORD_LENGTH; c++) {
      const tile = document.createElement("div");
      tile.className = "tile";
      tile.dataset.row = r;
      tile.dataset.col = c;
      board.appendChild(tile);
      rowTiles.push(tile);
    }
    tiles.push(rowTiles);
  }
}

async function fetchWord() {
  try {
    const params = new URLSearchParams({ mode: GAME_MODE, length: WORD_LENGTH });
    const res  = await fetch(`/api/word?${params}`);
    const data = await res.json();
    secretWord = data.word;
  } catch (e) {
    showToast("Failed to load word. Please refresh.");
  }
}

// ─── Input ────────────────────────────────────────────────────
function addEventListeners() {
  document.addEventListener("keydown", onKeydown);
  keyboard.querySelectorAll(".key").forEach(btn => {
    btn.addEventListener("click", () => handleKey(btn.dataset.key));
  });
  const hintBtn   = document.getElementById("btn-hint");
  const giveupBtn = document.getElementById("btn-giveup");
  if (hintBtn)   hintBtn.addEventListener("click", handleHint);
  if (giveupBtn) giveupBtn.addEventListener("click", handleGiveUp);
}

function onKeydown(e) {
  if (e.ctrlKey || e.altKey || e.metaKey) return;
  if (e.key === "Enter")     handleKey("ENTER");
  else if (e.key === "Backspace") handleKey("BACKSPACE");
  else if (/^[a-zA-Z]$/.test(e.key)) handleKey(e.key.toUpperCase());
}

function handleKey(key) {
  if (gameOver) return;
  if (key === "ENTER") submitGuess();
  else if (key === "BACKSPACE") deleteLetter();
  else if (/^[A-Z]$/.test(key) && currentGuess.length < WORD_LENGTH) typeLetter(key);
}

function typeLetter(letter) {
  const tile = tiles[currentRow][currentCol];
  tile.textContent = letter;
  tile.classList.add("filled");
  currentGuess.push(letter);
  currentCol++;
}

function deleteLetter() {
  if (currentCol <= 0) return;
  currentCol--;
  currentGuess.pop();
  const tile = tiles[currentRow][currentCol];
  tile.textContent = "";
  tile.classList.remove("filled");
}

// ─── Submit ───────────────────────────────────────────────────
async function submitGuess() {
  if (currentGuess.length < WORD_LENGTH) {
    showToast(`Need ${WORD_LENGTH} letters!`);
    shakeRow(currentRow);
    return;
  }

  const guess = currentGuess.join("");

  try {
    const res  = await fetch("/api/guess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guess, answer: secretWord })
    });
    const data = await res.json();

    if (!data.valid) {
      showToast("Not a valid word!");
      shakeRow(currentRow);
      return;
    }

    await revealRow(data.result);
    updateKeyboard(data.result);

    if (data.won) {
      gameOver = true;
      saveStats(true);
      const msgs = ["Genius!","Magnificent!","Impressive!","Splendid!","Great!","Phew!"];
      setTimeout(() => {
        bounceRow(currentRow);
        showResult(true, msgs[currentRow] || "Got it!");
        hideActionButtons();
      }, 400);
    } else {
      currentRow++;
      currentCol    = 0;
      currentGuess  = [];
      updateGuessCounter();
      if (currentRow >= MAX_GUESSES) {
        gameOver = true;
        saveStats(false);
        setTimeout(() => { showResult(false); hideActionButtons(); }, 400);
      }
    }
  } catch (e) {
    showToast("Network error. Try again.");
  }
}

// ─── Reveal animation ─────────────────────────────────────────
function revealRow(result) {
  return new Promise(resolve => {
    result.forEach((r, i) => {
      const tile = tiles[currentRow][i];
      setTimeout(() => {
        tile.classList.add("flip");
        setTimeout(() => {
          tile.classList.remove("filled");
          tile.classList.add("revealed", r.status);
        }, 250);
      }, i * 120);
    });
    setTimeout(resolve, result.length * 120 + 300);
  });
}

function bounceRow(row) {
  tiles[row].forEach((tile, i) => {
    setTimeout(() => tile.classList.add("bounce"), i * 80);
  });
}

function shakeRow(row) {
  const rowEls = tiles[row];
  rowEls.forEach(t => t.classList.add("row-shake"));
  setTimeout(() => rowEls.forEach(t => t.classList.remove("row-shake")), 500);
}

// ─── Keyboard coloring ────────────────────────────────────────
function updateKeyboard(result) {
  const priority = { correct: 3, present: 2, absent: 1 };
  result.forEach(({ letter, status }) => {
    const btn = keyboard.querySelector(`[data-key="${letter}"]`);
    if (!btn) return;
    const cur = priority[btn.dataset.state] || 0;
    if (priority[status] > cur) {
      btn.className = `key ${status}`;
      btn.dataset.state = status;
      if (btn.classList.contains("key-wide")) btn.classList.add("key-wide");
    }
  });
}

// ─── Result ───────────────────────────────────────────────────
function showResult(won, message = "") {
  resultPanel.classList.remove("d-none");
  resultAd.classList.remove("d-none");

  const emojis    = document.getElementById("result-emoji");
  const msgEl     = document.getElementById("result-message");
  const wordEl    = document.getElementById("result-word");
  const shareBtn  = document.getElementById("btn-share");
  const againBtn  = document.getElementById("btn-play-again");

  emojis.textContent  = won ? "🎉" : "😔";
  msgEl.textContent   = won ? message : "Better luck next time!";
  wordEl.textContent  = `The word was: ${secretWord}`;

  if (shareBtn) shareBtn.onclick = shareResult;
  if (againBtn) againBtn.onclick = resetGame;

  // Fetch & display word definition
  fetchDefinition(secretWord);
}

// ─── Word Definition (on game end) ────────────────────────────
async function fetchDefinition(word) {
  const card     = document.getElementById("definition-card");
  const loading  = document.getElementById("definition-loading");
  const defWord  = document.getElementById("def-word");
  const defPos   = document.getElementById("def-pos");
  const defText  = document.getElementById("def-text");
  const defEx    = document.getElementById("def-example");

  if (!card || !loading) return;

  loading.classList.remove("d-none");
  card.classList.add("d-none");

  try {
    const res  = await fetch(`/api/hint?word=${word.toLowerCase()}`);
    const data = await res.json();

    loading.classList.add("d-none");

    if (data.definition && !data.definition.startsWith("Starts with")) {
      defWord.textContent  = data.word || word.toUpperCase();
      defPos.textContent   = data.partOfSpeech || "";
      defPos.classList.toggle("d-none", !data.partOfSpeech);
      defText.textContent  = data.definition;
      defEx.textContent    = data.example ? `"${data.example}"` : "";
      defEx.classList.toggle("d-none", !data.example);
      card.classList.remove("d-none");
    }
  } catch (e) {
    loading.classList.add("d-none");
  }
}

function buildShareText(won) {
  // Score line: X/6 for win, X/6 for loss
  const guessCount = won ? (currentRow + 1) : "X";
  const today = new Date().toISOString().slice(0, 10);

  // Mode header
  let header = "WordMaster";
  if (GAME_MODE === "daily") {
    // Compute puzzle number (days since launch 2026-03-15)
    const launch = new Date("2026-03-15T00:00:00");
    const diff = Math.floor((new Date(today) - launch) / 86400000) + 1;
    header = `WordMaster Daily #${diff}`;
  } else if (GAME_MODE === "easy") {
    header = "WordMaster Easy";
  } else if (GAME_MODE === "hard") {
    header = "WordMaster Hard";
  } else if (GAME_MODE.startsWith("category_")) {
    const cat = GAME_MODE.replace("category_", "");
    header = `WordMaster ${cat.charAt(0).toUpperCase() + cat.slice(1)}`;
  }

  let text = `${header}  ${guessCount}/${MAX_GUESSES}\n`;
  text += `📅 ${today}\n\n`;

  const maxRow = won ? currentRow : MAX_GUESSES - 1;
  for (let r = 0; r <= maxRow; r++) {
    const row = tiles[r];
    if (!row.some(t => t.classList.contains("revealed"))) break;
    text += row.map(t => {
      if (t.classList.contains("correct"))  return "🟦";
      if (t.classList.contains("present"))  return "🟨";
      if (t.classList.contains("absent"))   return "⬜";
      return "⬛";
    }).join("") + "\n";
  }

  text += "\n🔗 wordmaster.store";
  return text;
}

async function shareResult() {
  const won  = gameOver && tiles[currentRow] &&
               tiles[Math.min(currentRow, MAX_GUESSES-1)]
                 .every(t => t.classList.contains("correct"));
  const text = buildShareText(won);

  // Try Web Share API first (mobile-friendly)
  if (navigator.share) {
    try {
      await navigator.share({ title: "WordMaster", text });
      return;
    } catch (e) {
      // User cancelled or share failed — fall through to clipboard
    }
  }

  // Clipboard fallback
  try {
    await navigator.clipboard.writeText(text);
    showShareFeedback("✅ Copied to clipboard!");
  } catch (e) {
    prompt("Copy your result:", text);
  }
}

function showShareFeedback(msg) {
  const btn = document.getElementById("btn-share");
  if (!btn) { showToast(msg); return; }
  const original = btn.innerHTML;
  btn.innerHTML = `<i class="bi bi-check-lg me-1"></i>${msg}`;
  btn.classList.add("btn-success");
  btn.classList.remove("btn-outline-primary");
  setTimeout(() => {
    btn.innerHTML = original;
    btn.classList.remove("btn-success");
    btn.classList.add("btn-outline-primary");
  }, 2500);
}

async function resetGame() {
  gameOver      = false;
  currentRow    = 0;
  currentCol    = 0;
  currentGuess  = [];
  hintUsed      = false;
  resultPanel.classList.add("d-none");
  resultAd.classList.add("d-none");
  const defCard = document.getElementById("definition-card");
  if (defCard) defCard.classList.add("d-none");
  const defLoading = document.getElementById("definition-loading");
  if (defLoading) defLoading.classList.add("d-none");
  keyboard.querySelectorAll(".key").forEach(btn => {
    btn.className = btn.classList.contains("key-wide") ? "key key-wide" : "key";
    delete btn.dataset.state;
  });
  // Reset hint button
  const hintBtn = document.getElementById("btn-hint");
  if (hintBtn) {
    hintBtn.disabled = false;
    hintBtn.innerHTML = '<i class="bi bi-lightbulb me-1"></i>Hint <span class="badge bg-warning text-dark ms-1">1</span>';
  }
  const hintPanel = document.getElementById("hint-panel");
  if (hintPanel) hintPanel.classList.add("d-none");
  // Show action buttons
  const actionBtns = document.getElementById("action-buttons");
  if (actionBtns) actionBtns.classList.remove("d-none");
  // Reset counter
  updateGuessCounter();
  buildBoard();
  await fetchWord();
}

// ─── Guess Counter ────────────────────────────────────────────
function updateGuessCounter() {
  const el = document.getElementById("guess-current");
  if (el) el.textContent = currentRow + 1;
}

// ─── Stats ────────────────────────────────────────────────────
function saveStats(won) {
  const defaults = { played: 0, won: 0, streak: 0, best: 0, dist: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 } };
  const stats = JSON.parse(localStorage.getItem("wm_stats") || JSON.stringify(defaults));

  if (GAME_MODE === "daily") {
    const today = new Date().toISOString().slice(0, 10);
    if (stats.lastDaily === today) return;
    stats.lastDaily = today;
  }

  stats.played++;
  if (won) {
    stats.won++;
    stats.streak++;
    if (stats.streak > stats.best) stats.best = stats.streak;
    const guessNum = currentRow + 1;
    stats.dist[guessNum] = (stats.dist[guessNum] || 0) + 1;
  } else {
    stats.streak = 0;
  }

  localStorage.setItem("wm_stats", JSON.stringify(stats));
}

// ─── Give Up ──────────────────────────────────────────────────
async function handleGiveUp() {
  if (gameOver) return;
  if (!confirm("Give up? The answer will be revealed.")) return;
  gameOver = true;
  saveStats(false);
  hideActionButtons();
  setTimeout(() => showResult(false), 200);
}

// ─── Hint ─────────────────────────────────────────────────────
async function handleHint() {
  if (gameOver || hintUsed) return;
  hintUsed = true;
  const hintBtn = document.getElementById("btn-hint");
  if (hintBtn) {
    hintBtn.disabled = true;
    hintBtn.innerHTML = '<i class="bi bi-lightbulb-off me-1"></i>Hint Used';
  }
  try {
    const res  = await fetch(`/api/hint?word=${secretWord.toLowerCase()}`);
    const data = await res.json();
    const panel   = document.getElementById("hint-panel");
    const content = document.getElementById("hint-content");
    if (panel && content) {
      let html = '<strong><i class="bi bi-lightbulb-fill me-1 text-warning"></i>Hint</strong>';
      if (data.partOfSpeech) html += ` <em class="text-muted">(${data.partOfSpeech})</em>`;
      html += `<br>${data.definition}`;
      if (data.example) html += `<br><small class="text-muted fst-italic">e.g. "${data.example}"</small>`;
      content.innerHTML = html;
      panel.classList.remove("d-none");
    }
  } catch (e) {
    showToast("Could not load hint.");
  }
}

function hideActionButtons() {
  const el = document.getElementById("action-buttons");
  if (el) el.classList.add("d-none");
}

// ─── Toast ────────────────────────────────────────────────────
let toastTimer;
function showToast(msg) {
  clearTimeout(toastTimer);
  toastArea.innerHTML = `<span class="toast-msg">${msg}</span>`;
  toastTimer = setTimeout(() => { toastArea.innerHTML = ""; }, 2100);
}

// ─── Start ────────────────────────────────────────────────────
init();
