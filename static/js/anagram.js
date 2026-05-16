// Anagram puzzle: scramble a target word; user clicks letters to arrange them back.
// Reads word from /api/word (or wm_custom_words localStorage for custom mode).

const WORD_LENGTH = window.WORD_LENGTH || 5;
const GAME_MODE   = window.GAME_MODE   || "standard";

let secretWord = "";
let scrambled  = [];
let slots      = [];
let usedIdx    = new Set();
let attempts   = 0;
let hintUsed   = false;
let gameOver   = false;

async function fetchWord() {
  if (GAME_MODE === "custom") {
    const arr = (JSON.parse(localStorage.getItem("wm_custom_words") || "[]") || [])
      .filter(w => typeof w === "string" && w.length === WORD_LENGTH && /^[A-Za-z]+$/.test(w));
    if (!arr.length) {
      showToast("Add custom words at /custom first.", 4000);
      secretWord = "";
      return;
    }
    secretWord = arr[Math.floor(Math.random() * arr.length)].toUpperCase();
    return;
  }
  try {
    const params = new URLSearchParams({ mode: GAME_MODE, length: WORD_LENGTH });
    const res = await fetch(`/api/word?${params}`);
    const data = await res.json();
    secretWord = (data.word || "").toUpperCase();
  } catch (e) {
    showToast("Could not load word.");
  }
}

function shuffleArray(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  // re-shuffle if accidentally matches original
  if (a.join("") === secretWord && arr.length > 1) return shuffleArray(arr);
  return a;
}

function newRound() {
  if (!secretWord) return;
  scrambled = shuffleArray(secretWord.split(""));
  slots = Array(secretWord.length).fill("");
  usedIdx.clear();
  attempts = 0;
  hintUsed = false;
  gameOver = false;
  document.getElementById("result-panel").classList.add("d-none");
  document.getElementById("btn-hint").disabled = false;
  render();
}

function render() {
  const slotsEl = document.getElementById("slots");
  slotsEl.innerHTML = slots.map((s, i) =>
    `<button class="anagram-slot ${s ? 'filled' : ''}" data-slot="${i}" type="button">${s || '·'}</button>`
  ).join("");

  const scrEl = document.getElementById("scrambled");
  scrEl.innerHTML = scrambled.map((s, i) =>
    `<button class="anagram-tile ${usedIdx.has(i) ? 'used' : ''}" data-letter-idx="${i}" ${usedIdx.has(i) ? 'disabled' : ''} type="button">${s}</button>`
  ).join("");
}

function placeLetter(letterIdx) {
  if (gameOver || usedIdx.has(letterIdx)) return;
  const slotIdx = slots.findIndex(s => s === "");
  if (slotIdx === -1) return;
  slots[slotIdx] = scrambled[letterIdx];
  usedIdx.add(letterIdx);
  render();
  if (slots.every(s => s !== "")) setTimeout(checkAnswer, 280);
}

function returnFromSlot(slotIdx) {
  if (gameOver) return;
  const letter = slots[slotIdx];
  if (!letter) return;
  for (const idx of usedIdx) {
    if (scrambled[idx] === letter) {
      usedIdx.delete(idx);
      break;
    }
  }
  slots[slotIdx] = "";
  render();
}

function checkAnswer() {
  attempts++;
  const guess = slots.join("");
  if (guess === secretWord) {
    win();
  } else {
    shakeEl(document.getElementById("slots"));
    setTimeout(() => {
      slots = Array(secretWord.length).fill("");
      usedIdx.clear();
      render();
      showToast(`Not quite — attempt ${attempts}, try again.`);
    }, 550);
  }
}

function win() {
  gameOver = true;
  window.wmSaveVocab(secretWord, true, attempts, "anagram");
  const panel = document.getElementById("result-panel");
  panel.classList.remove("d-none");
  document.getElementById("result-emoji").textContent = "🎉";
  document.getElementById("result-message").textContent = attempts === 1
    ? "Solved on the first try."
    : `Solved in ${attempts} ${attempts === 2 ? "attempt" : "attempts"}.`;
  document.getElementById("result-word").textContent = `The word: ${secretWord}`;
  fetchDefinition();
}

function giveUp() {
  if (gameOver) return;
  gameOver = true;
  window.wmSaveVocab(secretWord, false, attempts, "anagram");
  const panel = document.getElementById("result-panel");
  panel.classList.remove("d-none");
  document.getElementById("result-emoji").textContent = "😔";
  document.getElementById("result-message").textContent = "Next round will be easier.";
  document.getElementById("result-word").textContent = `The word was: ${secretWord}`;
  fetchDefinition();
}

async function fetchDefinition() {
  if (!secretWord) return;
  const defEl = document.getElementById("definition");
  if (!defEl) return;
  defEl.textContent = "Loading definition...";
  try {
    const res = await fetch(`/api/hint?word=${secretWord.toLowerCase()}`);
    const data = await res.json();
    let line = "";
    if (data.partOfSpeech) line += `(${data.partOfSpeech}) `;
    if (data.definition)   line += data.definition;
    if (data.example)      line += ` — "${data.example}"`;
    defEl.textContent = line || "";
  } catch (e) {
    defEl.textContent = "";
  }
}

function shuffleVisible() {
  if (gameOver) return;
  scrambled = shuffleArray(secretWord.split(""));
  slots = Array(secretWord.length).fill("");
  usedIdx.clear();
  render();
}

function clearSlots() {
  if (gameOver) return;
  slots = Array(secretWord.length).fill("");
  usedIdx.clear();
  render();
}

async function showHint() {
  if (gameOver || hintUsed) return;
  hintUsed = true;
  document.getElementById("btn-hint").disabled = true;
  // Place first letter into first slot
  const first = secretWord[0];
  for (let i = 0; i < scrambled.length; i++) {
    if (scrambled[i] === first && !usedIdx.has(i)) {
      // Clear slot 0 if occupied
      if (slots[0]) returnFromSlot(0);
      slots[0] = first;
      usedIdx.add(i);
      break;
    }
  }
  render();
  showToast("Hint: first letter placed.");
}

function shakeEl(el) {
  el.classList.add("shake");
  setTimeout(() => el.classList.remove("shake"), 450);
}

let toastTimer;
function showToast(msg, duration = 2200) {
  const t = document.getElementById("toast-area");
  if (!t) return;
  t.textContent = msg;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.textContent = ""; }, duration);
}

function attachEvents() {
  document.getElementById("scrambled").addEventListener("click", e => {
    const idx = e.target.dataset.letterIdx;
    if (idx !== undefined) placeLetter(parseInt(idx, 10));
  });
  document.getElementById("slots").addEventListener("click", e => {
    const idx = e.target.dataset.slot;
    if (idx !== undefined) returnFromSlot(parseInt(idx, 10));
  });
  document.getElementById("btn-shuffle").addEventListener("click", shuffleVisible);
  document.getElementById("btn-clear").addEventListener("click", clearSlots);
  document.getElementById("btn-hint").addEventListener("click", showHint);
  document.getElementById("btn-giveup").addEventListener("click", giveUp);
  document.getElementById("btn-new").addEventListener("click", async () => {
    await fetchWord();
    newRound();
  });
}

(async function init() {
  attachEvents();
  await fetchWord();
  newRound();
})();
