
(() => {
  "use strict";

  const boardEl = document.getElementById("board");
  const titleEl = document.getElementById("lesson-title");
  const metaEl = document.getElementById("lesson-meta");
  const promptEl = document.getElementById("lesson-prompt");
  const feedbackEl = document.getElementById("feedback");

  const submitBtn = document.getElementById("submit-move");
  const resetBtn = document.getElementById("reset-position");
  const clearBtn = document.getElementById("clear-selection");

  let game = null;
  let board = null;

  let currentLesson = 1;
  let startingFen = null;

  let selected = null;
  let legalTargets = [];
  let selectedMove = null;

  function say(text, kind = "") {
    feedbackEl.textContent = text;
    feedbackEl.className =
      "feedback" + (kind ? " " + kind : "");
  }

  // Highlight selected square and legal destinations.
  function updateHighlights() {
    boardEl.querySelectorAll("[data-square]").forEach(square => {
      const name = square.getAttribute("data-square");

      square.classList.remove(
        "strategy-selected",
        "strategy-target",
        "strategy-capture"
      );

      if (name === selected) {
        square.classList.add("strategy-selected");
      }

      if (legalTargets.includes(name)) {
        square.classList.add("strategy-target");

        if (game.get(name)) {
          square.classList.add("strategy-capture");
        }
      }
    });
  }

  function clearMoveSelection() {
    selected = null;
    legalTargets = [];
    selectedMove = null;

    submitBtn.disabled = true;

    updateHighlights();
  }

  // Save a successfully made move for server-side checking.
  
  function finishMove(move, syncBoard = true) {
    selectedMove = {
        from: move.from,
        to: move.to,
        promotion: move.promotion || ""
    };

    selected = null;
    legalTargets = [];

    submitBtn.disabled = false;

    // Synchronize without animation to prevent duplicate movement.
    if (syncBoard) {
        board.position(game.fen(), false);
    }

    updateHighlights();

    say(
        "Move selected: " + move.san +
        ". Submit it to check your decision."
    );
}

  // DRAGGING: prevent dragging the opponent's pieces.
  function onDragStart(source, piece) {
    if (!game) return false;
    if (game.game_over()) return false;
    if (piece[0] !== game.turn()) return false;

    clearMoveSelection();

    return true;
}

  // DRAGGING: validate and process the move.
  function onDrop(source, target) {
    if (!game) return "snapback";

    const move = game.move({
        from: source,
        to: target,
        promotion: "q"
    });

    if (!move) {
        return "snapback";
    }

    finishMove(move, false);
}


  // Keep the displayed board synchronized with chess.js.
 function onSnapEnd() {
    if (game) {
        board.position(game.fen(), false);
        updateHighlights();
    }
}

  // CLICKING: select a piece, then click its destination.
  function onSquareClick(square) {
    if (!game) return;

    const piece = game.get(square);

    // A destination square was clicked.
    if (selected && legalTargets.includes(square)) {
      const move = game.move({
        from: selected,
        to: square,
        promotion: "q"
      });

      if (move) {
        finishMove(move);
        return;
      }
    }

    // Select a piece belonging to the side to move.
    if (piece && piece.color === game.turn()) {
      selected = square;

      legalTargets = game.moves({
        square: square,
        verbose: true
      }).map(move => move.to);

      selectedMove = null;
      submitBtn.disabled = true;

      updateHighlights();

      say("Choose a highlighted destination square.");
      return;
    }

    clearMoveSelection();

    say("Select one of your pieces, then choose a legal destination.");
  }

  // Listen for clicks on chessboard.js squares.
  boardEl.addEventListener("click", event => {
    const squareElement = event.target.closest("[data-square]");

    if (!squareElement) return;

    const square = squareElement.getAttribute("data-square");

    onSquareClick(square);
  });

  async function loadLesson(id) {
    say("Loading lesson…");

    try {
      const response = await fetch(
        "/api/strategy/lesson/" + id
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Could not load this lesson."
        );
      }

      currentLesson = id;
      startingFen = data.fen;

      game = new Chess(startingFen);

      clearMoveSelection();

      titleEl.textContent = data.title;

      metaEl.textContent =
        "Lesson " + data.id +
        " · " + data.level +
        " · " + data.theme;

      promptEl.textContent = data.prompt;

      board.position(game.fen());

      updateHighlights();

      say("Select a legal move using either dragging or clicking.");
    } catch (err) {
      say(err.message, "bad");
    }
  }

  // Submit the selected move to Flask.
  submitBtn.addEventListener("click", async () => {
    if (!selectedMove) return;

    const uci =
      selectedMove.from +
      selectedMove.to +
      selectedMove.promotion;

    submitBtn.disabled = true;

    try {
      const response = await fetch(
        "/api/strategy/answer",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            lesson_id: currentLesson,
            move_uci: uci
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Could not check this move."
        );
      }

      document.getElementById("score").textContent =
        data.score;

      document.getElementById("attempts").textContent =
        data.attempts;

      document.getElementById("accuracy").textContent =
        data.accuracy + "%";

      say(
        (data.correct
          ? "Correct! "
          : "Not the target move. Your move: " +
            data.chosen_san +
            ". Suggested move: " +
            data.correct_san + ". ") +
        data.explanation + " " + data.why_not,

        data.correct ? "good" : "bad"
      );

    } catch (err) {
      say(err.message, "bad");
    }

    clearMoveSelection();
  });

  // Reset the current position.
  resetBtn.addEventListener("click", () => {
    if (!startingFen) return;

    game = new Chess(startingFen);

    board.position(game.fen());

    clearMoveSelection();

    say("Position reset. Try again.");
  });

  // Clear current selection.
  clearBtn.addEventListener("click", () => {
    clearMoveSelection();

    say("Selection cleared.");
  });

  // Load lessons.
  document.querySelectorAll(".load-lesson").forEach(btn => {
    btn.addEventListener("click", () => {
      loadLesson(Number(btn.dataset.lesson));
    });
  });

  // Check required libraries.
  if (
    typeof Chess === "undefined" ||
    typeof Chessboard === "undefined"
  ) {
    say(
      "Chessboard libraries could not load. Check your internet connection.",
      "bad"
    );
    return;
  }

  // Create the board using the same piece images as Openings.
  board = Chessboard("board", {
    position: "start",
    draggable: true,

    pieceTheme:
      "https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png",

    onDragStart: onDragStart,
    onDrop: onDrop,
    onSnapEnd: onSnapEnd
  });

  window.addEventListener("resize", () => {
    board.resize();
  });

  loadLesson(1);

})();
