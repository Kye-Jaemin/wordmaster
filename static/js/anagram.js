// Anagram puzzle: scramble a target word; user clicks letters to arrange them back.
// Reads word from /api/word (or wm_custom_words localStorage for custom mode).

// ─── i18n ────────────────────────────────────────────────────
const _KO = {
  needCustom:      "먼저 /custom 에서 단어를 추가하세요.",
  failedLoad:      "단어를 불러올 수 없습니다.",
  tryAgain:        (n) => `아쉽네요 — ${n}번째 시도, 다시 해보세요.`,
  solvedFirst:     "첫 시도에 풀었어요.",
  solvedInN:       (n) => `${n}번 시도 만에 풀었어요.`,
  theWord:         (w) => `정답: ${w}`,
  betterLuck:      "다음 라운드는 더 쉬울 거예요.",
  theWordWas:      (w) => `정답은: ${w} 였어요.`,
  hintPlaced:      "힌트: 글자 하나가 배치됐어요.",
};
const _EN = {
  needCustom:      "Add custom words at /custom first.",
  failedLoad:      "Could not load word.",
  tryAgain:        (n) => `Not quite — attempt ${n}, try again.`,
  solvedFirst:     "Solved on the first try.",
  solvedInN:       (n) => `Solved in ${n} ${n === 2 ? "attempt" : "attempts"}.`,
  theWord:         (w) => `The word: ${w}`,
  betterLuck:      "Next round will be easier.",
  theWordWas:      (w) => `The word was: ${w}`,
  hintPlaced:      "Hint: a letter was placed.",
};
const T = (typeof window.WM_LANG !== "undefined" && window.WM_LANG === "ko") ? _KO : _EN;

const WORD_LENGTH = window.WORD_LENGTH || 5;
const GAME_MODE   = window.GAME_MODE   || "standard";

let secretWord = "";
let scrambled  = [];
let slots      = [];
let usedIdx    = new Set();
let attempts   = 0;
let gameOver   = false;

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
  gameOver = false;
  updateAttemptCount();
  document.getElementById("result-panel").classList.add("d-none");
  document.getElementById("btn-hint").disabled = false;
  // Auto-show the spoiler-safe meaning clue so the player has somewhere to start
  if (window.wmShowClue) window.wmShowClue(secretWord);
  // Hide the post-game result ad + Word Learning Card when starting fresh
  const resultAd = document.getElementById("result-ad");
  if (resultAd) resultAd.classList.add("d-none");
  const wlCard = document.getElementById("word-learning-card");
  if (wlCard) wlCard.classList.add("d-none");
  render();
}

function updateAttemptCount() {
  const el = document.getElementById("attempt-count");
  if (el) el.textContent = attempts;
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
  updateAttemptCount();
  const guess = slots.join("");
  if (guess === secretWord) {
    win();
  } else {
    shakeEl(document.getElementById("slots"));
    setTimeout(() => {
      slots = Array(secretWord.length).fill("");
      usedIdx.clear();
      render();
      showToast(T.tryAgain(attempts));
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
    ? T.solvedFirst
    : T.solvedInN(attempts);
  document.getElementById("result-word").textContent = T.theWord(secretWord);
  fetchDefinition();
}

function giveUp() {
  if (gameOver) return;
  gameOver = true;
  window.wmSaveVocab(secretWord, false, attempts, "anagram");
  const panel = document.getElementById("result-panel");
  panel.classList.remove("d-none");
  document.getElementById("result-emoji").textContent = "😔";
  document.getElementById("result-message").textContent = T.betterLuck;
  document.getElementById("result-word").textContent = T.theWordWas(secretWord);
  fetchDefinition();
}

function fetchDefinition() {
  // Delegates to the shared learning-storage helper so all puzzle formats
  // populate the same rich Word Learning Card (phonetic, meanings, synonyms,
  // antonyms, etymology). Also reveals the result AdSense block.
  // In News mode, also surfaces the headline this word came from.
  if (!secretWord) return;
  if (window.wmPopulateLearningCard) window.wmPopulateLearningCard(secretWord);
  if (window.wmShowResultAd)         window.wmShowResultAd();
  if (typeof window.revealNewsSource === "function") window.revealNewsSource();
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

// Rebuild usedIdx (which scrambled tiles are consumed) from the current slots,
// matching letters greedily. Used after a hint sets a slot directly.
function syncUsedFromSlots() {
  usedIdx.clear();
  const avail = scrambled.map(() => true);
  for (const ch of slots) {
    if (!ch) continue;
    for (let i = 0; i < scrambled.length; i++) {
      if (avail[i] && scrambled[i] === ch) { avail[i] = false; usedIdx.add(i); break; }
    }
  }
}

// Lock the correct letter into the next not-yet-correct slot. Repeatable.
function revealAnagramLetter() {
  if (gameOver) return;
  let p = -1;
  for (let i = 0; i < secretWord.length; i++) {
    if (slots[i] !== secretWord[i]) { p = i; break; }
  }
  if (p === -1) return; // already all correct
  const need = secretWord[p];
  // Drop wrong placements of the same letter elsewhere so tile counts stay valid
  for (let i = 0; i < slots.length; i++) {
    if (i !== p && slots[i] === need && slots[i] !== secretWord[i]) slots[i] = "";
  }
  slots[p] = need;
  syncUsedFromSlots();
  render();
  showToast(T.hintPlaced);
  if (slots.every(s => s !== "")) setTimeout(checkAnswer, 280);
}

// Hint button: watch a rewarded ad, then reveal one letter
function handleAdHint() {
  if (gameOver) return;
  if (window.wmWatchAdForReward) window.wmWatchAdForReward(revealAnagramLetter);
  else revealAnagramLetter();
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
