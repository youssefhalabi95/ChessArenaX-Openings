const PIECES = {
  K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙",
  k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟"
};
const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];

let currentLesson = null;
let exIndex = 0;
let selectedSq = null;
let draggedSq = null;
let lastMoveUci = null;
let lastSubmittedMove = null; // { fromSq, toSq, piece }

function parseBoard(fen) {
  const placement = fen.split(" ")[0].split("/");
  const map = {};
  for (let r = 0; r < 8; r++) {
    let f = 0;
    for (const ch of placement[r]) {
      if (/[1-8]/.test(ch)) {
        f += parseInt(ch, 10);
      } else {
        const sq = FILES[f] + (8 - r);
        map[sq] = ch;
        f++;
      }
    }
  }
  return map;
}

function getDisplayPosition(ex) {
  const pos = parseBoard(ex.fen);
  if (lastSubmittedMove && pos[lastSubmittedMove.fromSq]) {
    const movingPiece = pos[lastSubmittedMove.fromSq];
    delete pos[lastSubmittedMove.fromSq];
    pos[lastSubmittedMove.toSq] = movingPiece;
  }
  return pos;
}

function renderCoordinates(flipped) {
  const ranks = flipped ? [1, 2, 3, 4, 5, 6, 7, 8] : [8, 7, 6, 5, 4, 3, 2, 1];
  const files = flipped ? [...FILES].reverse() : FILES;

  document.getElementById("ranks").innerHTML = ranks.map(r => `<div>${r}</div>`).join("");
  document.getElementById("files").innerHTML = files.map(f => `<div>${f}</div>`).join("");
  return { ranks, files };
}

function renderBoard() {
  const ex = currentLesson.exercises[exIndex];
  const pos = getDisplayPosition(ex);
  const flipped = ex.orientation === "black";
  const { ranks, files } = renderCoordinates(flipped);

  const fromSq = lastMoveUci ? lastMoveUci.slice(0, 2) : null;
  const toSq = lastMoveUci ? lastMoveUci.slice(2, 4) : null;

  const boardEl = document.getElementById("board");
  boardEl.innerHTML = "";

  ranks.forEach((rk, rIdx) => {
    files.forEach((fl, fIdx) => {
      const sq = fl + rk;
      const isLight = (rIdx + fIdx) % 2 === 0;
      const piece = pos[sq];

      const div = document.createElement("div");
      div.className = `sq ${isLight ? "light" : "dark"}`;
      div.dataset.sq = sq;
      if (selectedSq === sq) div.classList.add("selected");
      if (sq === fromSq || sq === toSq) div.classList.add("last-move");

      if (piece) {
        const pieceSpan = document.createElement("span");
        pieceSpan.className = "piece-span " + (piece === piece.toUpperCase() ? "piece-white" : "piece-black");
        pieceSpan.textContent = PIECES[piece];
        pieceSpan.draggable = true;

        pieceSpan.addEventListener("dragstart", (e) => {
          draggedSq = sq;
          selectedSq = sq;
          e.dataTransfer.setData("text/plain", sq);
          e.dataTransfer.effectAllowed = "move";
        });

        pieceSpan.addEventListener("dragend", () => {
          draggedSq = null;
          document.querySelectorAll(".sq.drag-over").forEach(el => el.classList.remove("drag-over"));
        });

        div.appendChild(pieceSpan);
      }

      div.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        div.classList.add("drag-over");
      });

      div.addEventListener("dragleave", () => {
        div.classList.remove("drag-over");
      });

      div.addEventListener("drop", async (e) => {
        e.preventDefault();
        div.classList.remove("drag-over");
        const fromSquare = draggedSq || e.dataTransfer.getData("text/plain");
        draggedSq = null;
        if (!fromSquare || fromSquare === sq) {
          selectedSq = null;
          renderBoard();
          return;
        }
        await commitMove(fromSquare, sq);
      });

      div.addEventListener("click", () => onSquareClick(sq));
      boardEl.appendChild(div);
    });
  });
}

function resetSelection() {
  selectedSq = null;
  draggedSq = null;
  lastSubmittedMove = null;
  lastMoveUci = null;
  renderBoard();
}

function showHint() {
  const ex = currentLesson.exercises[exIndex];
  const fb = document.getElementById("feedback");
  fb.className = "feedback try-again";
  fb.innerHTML = `<strong>Hint:</strong> ${ex.hint}`;
}

async function onSquareClick(sq) {
  if (!selectedSq) {
    selectedSq = sq;
    renderBoard();
    return;
  }
  if (selectedSq === sq) {
    selectedSq = null;
    renderBoard();
    return;
  }
  const fromSquare = selectedSq;
  selectedSq = null;
  await commitMove(fromSquare, sq);
}

async function commitMove(fromSquare, toSquare) {
  const uci = fromSquare + toSquare;
  lastSubmittedMove = { fromSq: fromSquare, toSq: toSquare };
  lastMoveUci = uci;
  renderBoard();
  await submitMove(uci);
}

async function submitMove(moveUci) {
  const res = await fetch("/api/strategy/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      lesson_id: currentLesson.id,
      exercise_index: exIndex,
      move_uci: moveUci
    })
  });
  const data = await res.json();
  const fb = document.getElementById("feedback");

  if (data.error) {
    lastSubmittedMove = null;
    lastMoveUci = null;
    renderBoard();
    fb.className = "feedback try-again";
    fb.textContent = data.error;
    return;
  }

  document.getElementById("stat-score").textContent = data.score;
  document.getElementById("stat-acc").textContent = `${data.accuracy}%`;

  if (data.correct) {
    fb.className = "feedback ok";
    fb.innerHTML = `<strong>${data.chosen_san} — Nice move!</strong><br>${data.explanation}<br><em>Next plan:</em> ${data.plan}`;
  } else {
    fb.className = "feedback try-again";
    fb.innerHTML = `<strong>${data.chosen_san} — Not quite.</strong><br>${data.explanation}<br><em>Hint:</em> ${data.plan}`;
  }
}

function selectExercise(idx) {
  exIndex = idx;
  selectedSq = null;
  draggedSq = null;
  lastSubmittedMove = null;
  lastMoveUci = null;
  document.getElementById("tab-0").classList.toggle("active", idx === 0);
  document.getElementById("tab-1").classList.toggle("active", idx === 1);

  const ex = currentLesson.exercises[exIndex];
  document.getElementById("ex-focus").textContent = `${ex.focus} · ${ex.side} to move`;
  document.getElementById("ex-prompt").textContent = ex.prompt;

  const fb = document.getElementById("feedback");
  fb.className = "feedback";
  fb.textContent = "Drag a piece to a square, or click a piece and click its destination square.";
  renderBoard();
}

async function loadLesson(id) {
  document.querySelectorAll(".lesson-btn").forEach(b => {
    b.classList.toggle("active", Number(b.dataset.id) === id);
  });
  const res = await fetch(`/api/strategy/lesson/${id}`);
  currentLesson = await res.json();

  document.getElementById("l-title").textContent = `${currentLesson.id}. ${currentLesson.title}`;
  document.getElementById("l-meta").textContent = `${currentLesson.level} · ${currentLesson.theme} · ${currentLesson.minutes}`;
  document.getElementById("l-obj").textContent = currentLesson.objective;
  document.getElementById("l-learn").innerHTML = currentLesson.learn
    .map(([k, v]) => `<li><strong>${k}:</strong> ${v}</li>`)
    .join("");
  document.getElementById("l-check").innerHTML = currentLesson.checklist
    .map(c => `<li>${c}</li>`)
    .join("");
  document.getElementById("l-takeaway").textContent = currentLesson.takeaway;

  selectExercise(0);
}

const initialLessonId = Number(document.body.dataset.initialLesson || 1);
loadLesson(initialLessonId);