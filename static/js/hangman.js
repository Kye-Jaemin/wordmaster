// Hangman puzzle: guess letters one at a time before lives run out.
// Reads word from /api/word (or wm_custom_words localStorage for custom mode).

const WORD_LENGTH = window.WORD_LENGTH || 5;
const GAME_MODE   = window.GAME_MODE   || "standard";
const MAX_LIVES   = 6;

let secretWord  = "";
let revealed    = [];
let wrongLetters = [];
let livesLeft   = MAX_LIVES;
let hintUsed    = false;
let gameOver    = false;

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

function newRound() {
  if (!secretWord) return;
  revealed = Array(secretWord.length).fill(false);
  wrongLetters = [];
  livesLeft = MAX_LIVES;
  hintUsed = false;
  gameOver = false;
  document.getElementById("result-panel").classList.add("d-none");
  const hintBtn = document.getElementById("btn-hint");
  if (hintBtn) hintBtn.disabled = false;
  document.querySelectorAll(".key[data-key]").forEach(b => b.classList.remove("correct", "absent"));
  render();
}

function render() {
  document.getElementById("word-display").innerHTML = secretWord.split("").map((l, i) =>
    `<span class="hangman-letter ${revealed[i] ? "revealed" : ""}">${revealed[i] ? l : "_"}</span>`
  ).join("");

  document.getElementById("lives-display").innerHTML =
    "❤️".repeat(livesLeft) + '<span class="opacity-25">' + "♡".repeat(MAX_LIVES - livesLeft) + "</span>";

  document.getElementById("wrong-display").textContent = wrongLetters.length
    ? "Wrong: " + wrongLetters.join("  ")
    : "";
}

function guess(letter) {
  if (gameOver) return;
  letter = letter.toUpperCase();
  if (!/^[A-Z]$/.test(letter)) return;
  // already used?
  if (wrongLetters.includes(letter)) return;
  if (secretWord.includes(letter) && revealed.some((r, i) => r && secretWord[i] === letter)) return;

  let hit = false;
  for (let i = 0; i < secretWord.length; i++) {
    if (secretWord[i] === letter) {
      revealed[i] = true;
      hit = true;
    }
  }
  const keyBtn = document.querySelector(`.key[data-key="${letter}"]`);
  if (hit) {
    if (keyBtn) keyBtn.classList.add("correct");
  } else {
    wrongLetters.push(letter);
    livesLeft--;
    if (keyBtn) keyBtn.classList.add("absent");
  }
  render();
  if (revealed.every(r => r)) win();
  else if (livesLeft <= 0) lose();
}

function win() {
  gameOver = true;
  window.wmSaveVocab(secretWord, true, MAX_LIVES - livesLeft, "hangman");
  const panel = document.getElementById("result-panel");
  panel.classList.remove("d-none");
  document.getElementById("result-emoji").textContent = "🎉";
  document.getElementById("result-message").textContent = wrongLetters.length === 0
    ? "Solved with no wrong letters."
    : `Solved with ${wrongLetters.length} wrong letter${wrongLetters.length > 1 ? "s" : ""}.`;
  document.getElementById("result-word").textContent = `The word: ${secretWord}`;
  fetchDefinition();
}

function lose() {
  gameOver = true;
  window.wmSaveVocab(secretWord, false, MAX_LIVES, "hangman");
  // reveal all
  revealed = Array(secretWord.length).fill(true);
  render();
  const panel = document.getElementById("result-panel");
  panel.classList.remove("d-none");
  document.getElementById("result-emoji").textContent = "😔";
  document.getElementById("result-message").textContent = "Out of lives. Next time.";
  document.getElementById("result-word").textContent = `The word was: ${secretWord}`;
  fetchDefinition();
}

function giveUp() {
  if (gameOver) return;
  livesLeft = 0;
  lose();
}

async function showHint() {
  if (gameOver || hintUsed) return;
  hintUsed = true;
  document.getElementById("btn-hint").disabled = true;
  // Reveal one unrevealed letter for free (no life cost)
  const candidates = [];
  for (let i = 0; i < secretWord.length; i++) {
    if (!revealed[i]) candidates.push(i);
  }
  if (candidates.length) {
    const pick = candidates[Math.floor(Math.random() * candidates.length)];
    revealed[pick] = true;
    const letter = secretWord[pick];
    const keyBtn = document.querySelector(`.key[data-key="${letter}"]`);
    if (keyBtn) keyBtn.classList.add("correct");
    render();
    showToast("Hint: revealed one letter.");
    if (revealed.every(r => r)) win();
  }
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

let toastTimer;
function showToast(msg, duration = 2200) {
  const t = document.getElementById("toast-area");
  if (!t) return;
  t.textContent = msg;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.textContent = ""; }, duration);
}

function attachEvents() {
  document.getElementById("keyboard").addEventListener("click", e => {
    const key = e.target.dataset.key;
    if (key) guess(key);
  });
  document.addEventListener("keydown", e => {
    if (e.key && /^[a-zA-Z]$/.test(e.key)) guess(e.key);
  });
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
