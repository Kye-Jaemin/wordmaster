// Hangman puzzle: guess letters one at a time before lives run out.
// Reads word from /api/word (or wm_custom_words localStorage for custom mode).

// ─── i18n ────────────────────────────────────────────────────
const _KO = {
  needCustom:      "먼저 /custom 에서 단어를 추가하세요.",
  failedLoad:      "단어를 불러올 수 없습니다.",
  wrongPrefix:     "오답: ",
  solvedClean:     "틀린 글자 없이 풀었어요.",
  solvedWithWrong: (n) => `틀린 글자 ${n}개로 풀었어요.`,
  theWord:         (w) => `정답: ${w}`,
  outOfLives:      "생명이 다 떨어졌어요. 다음 기회에.",
  theWordWas:      (w) => `정답은: ${w} 였어요.`,
  hintRevealed:    "힌트: 글자 하나가 공개됐어요.",
};
const _EN = {
  needCustom:      "Add custom words at /custom first.",
  failedLoad:      "Could not load word.",
  wrongPrefix:     "Wrong: ",
  solvedClean:     "Solved with no wrong letters.",
  solvedWithWrong: (n) => `Solved with ${n} wrong letter${n > 1 ? "s" : ""}.`,
  theWord:         (w) => `The word: ${w}`,
  outOfLives:      "Out of lives. Next time.",
  theWordWas:      (w) => `The word was: ${w}`,
  hintRevealed:    "Hint: revealed one letter.",
};
const T = (typeof window.WM_LANG !== "undefined" && window.WM_LANG === "ko") ? _KO : _EN;

const WORD_LENGTH = window.WORD_LENGTH || 5;
const GAME_MODE   = window.GAME_MODE   || "standard";
const MAX_LIVES   = 6;

let secretWord  = "";
let revealed    = [];
let wrongLetters = [];
let livesLeft   = MAX_LIVES;
let gameOver    = false;

async function fetchWord() {
  if (GAME_MODE === "custom") {
    const arr = (JSON.parse(localStorage.getItem("wm_custom_words") || "[]") || [])
      .filter(w => typeof w === "string" && w.length === WORD_LENGTH && /^[A-Za-z]+$/.test(w));
    if (!arr.length) {
      showToast(T.needCustom, 4000);
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
    showToast(T.failedLoad);
  }
}

function newRound() {
  if (!secretWord) return;
  revealed = Array(secretWord.length).fill(false);
  wrongLetters = [];
  livesLeft = MAX_LIVES;
  gameOver = false;
  document.getElementById("result-panel").classList.add("d-none");
  const hintBtn = document.getElementById("btn-hint");
  if (hintBtn) hintBtn.disabled = false;
  // Auto-show the spoiler-safe meaning clue so the player has somewhere to start
  if (window.wmShowClue) window.wmShowClue(secretWord);
  document.querySelectorAll(".key[data-key]").forEach(b => b.classList.remove("correct", "absent"));
  // Hide the post-game result ad + Word Learning Card when starting fresh
  const resultAd = document.getElementById("result-ad");
  if (resultAd) resultAd.classList.add("d-none");
  const wlCard = document.getElementById("word-learning-card");
  if (wlCard) wlCard.classList.add("d-none");
  render();
}

function render() {
  document.getElementById("word-display").innerHTML = secretWord.split("").map((l, i) =>
    `<span class="hangman-letter ${revealed[i] ? "revealed" : ""}">${revealed[i] ? l : "_"}</span>`
  ).join("");

  document.getElementById("lives-display").innerHTML =
    "❤️".repeat(livesLeft) + '<span class="opacity-25">' + "♡".repeat(MAX_LIVES - livesLeft) + "</span>";

  document.getElementById("wrong-display").textContent = wrongLetters.length
    ? T.wrongPrefix + wrongLetters.join("  ")
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
    ? T.solvedClean
    : T.solvedWithWrong(wrongLetters.length);
  document.getElementById("result-word").textContent = T.theWord(secretWord);
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
  document.getElementById("result-message").textContent = T.outOfLives;
  document.getElementById("result-word").textContent = T.theWordWas(secretWord);
  fetchDefinition();
}

function giveUp() {
  if (gameOver) return;
  livesLeft = 0;
  lose();
}

// Reveal one random unrevealed letter (no life cost). Repeatable.
function revealHangmanLetter() {
  if (gameOver) return;
  const candidates = [];
  for (let i = 0; i < secretWord.length; i++) {
    if (!revealed[i]) candidates.push(i);
  }
  if (!candidates.length) return;
  const pick = candidates[Math.floor(Math.random() * candidates.length)];
  revealed[pick] = true;
  const letter = secretWord[pick];
  const keyBtn = document.querySelector(`.key[data-key="${letter}"]`);
  if (keyBtn) keyBtn.classList.add("correct");
  render();
  showToast(T.hintRevealed);
  if (revealed.every(r => r)) win();
}

// Hint button: watch a rewarded ad, then reveal one letter
function handleAdHint() {
  if (gameOver) return;
  if (window.wmWatchAdForReward) window.wmWatchAdForReward(revealHangmanLetter);
  else revealHangmanLetter();
}

function fetchDefinition() {
  // Same shared population path that anagram and tile-guess use, so all
  // three puzzle formats present an identical post-game learning card.
  // In News mode, also surfaces the headline this word came from.
  if (!secretWord) return;
  if (window.wmPopulateLearningCard) window.wmPopulateLearningCard(secretWord);
  if (window.wmShowResultAd)         window.wmShowResultAd();
  if (typeof window.revealNewsSource === "function") window.revealNewsSource();
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
  document.getElementById("btn-hint").addEventListener("click", handleAdHint);
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
