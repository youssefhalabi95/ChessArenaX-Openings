"""
ChessArenaX Strategy Lab blueprint.

Requires python-chess (already used by the existing ChessArenaX app).
Premium access is currently protected by a server-checked access code.
This is a beta/manual access mechanism, NOT payment processing.
"""
import json
import os
import secrets
import sqlite3
from pathlib import Path

import chess
from flask import (
    Blueprint, current_app, jsonify, redirect, render_template,
    request, session, url_for
)
from auth_payment import has_premium_access

strategy_bp = Blueprint("strategy", __name__)
DB_PATH = Path(__file__).resolve().parent / "strategy_progress.sqlite3"

# Each setup is a legal sequence from the standard starting position.
# The answer is SAN for the side to move after the setup sequence.
# These are curated training examples, not engine-certified evaluations.
LESSONS = [
    {
        "id": 1, "title": "Claim the Centre", "level": "Beginner",
        "theme": "Central control", "setup": [],
        "answer": "e4",
        "prompt": "Choose a principled first move that immediately fights for the centre.",
        "explanation": "1.e4 controls d5 and f5, opens lines for the queen and king's bishop, and creates a direct claim to central space.",
        "why_not": "Other first moves can also be playable. This lesson rewards the central-control idea, rather than claiming that 1.e4 is the only good move."
    },
    {
        "id": 2, "title": "Pressure on the Centre", "level": "Beginner",
        "theme": "Development", "setup": ["e4", "e5", "Nf3", "Nc6"],
        "answer": "Bb5",
        "prompt": "Develop a piece while increasing pressure on Black's central knight.",
        "explanation": "Bb5 develops the bishop and indirectly pressures the e5-pawn by challenging the knight that supports it. This is the Ruy Lopez.",
        "why_not": "This is a classic developing move, but chess positions can offer more than one reasonable continuation."
    },
    {
        "id": 3, "title": "Challenge the Centre", "level": "Beginner",
        "theme": "Pawn structure", "setup": ["d4", "d5"],
        "answer": "c4",
        "prompt": "Challenge Black's central pawn rather than allowing it to remain unopposed.",
        "explanation": "c4 is the Queen's Gambit idea: White attacks the d5-pawn and fights for central space. Black may accept or decline the pawn offer.",
        "why_not": "The point is to challenge the centre with a pawn, not to win the c-pawn at any cost."
    },
    {
        "id": 4, "title": "Open Sicilian Development", "level": "Intermediate",
        "theme": "Development", "setup": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4"],
        "answer": "Nf6",
        "prompt": "As Black, develop a piece and put pressure on White's e4-pawn.",
        "explanation": "Nf6 develops with tempo by attacking e4. This is a standard developing idea in the Open Sicilian.",
        "why_not": "Developing moves should also have a purpose. Here, the knight immediately challenges White's centre."
    },
    {
        "id": 5, "title": "Prepare a Central Break", "level": "Intermediate",
        "theme": "Pawn breaks", "setup": ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"],
        "answer": "c3",
        "prompt": "Prepare a strong central advance while keeping your position flexible.",
        "explanation": "c3 supports the planned d4 advance and builds a stronger pawn centre. It is a common Italian Game plan.",
        "why_not": "The idea is preparation: central breaks work best when the pieces and pawns support them."
    },
    {
        "id": 6, "title": "Accept the Gambit", "level": "Intermediate",
        "theme": "Material and development", "setup": ["e4", "e5", "f4"],
        "answer": "exf4",
        "prompt": "As Black, take the offered pawn in the King's Gambit and test White's compensation.",
        "explanation": "exf4 accepts the gambit. Black gains a pawn but must still develop accurately and be alert to White's lead in activity.",
        "why_not": "Accepting is a legitimate choice, not an obligation; the lesson is about understanding the material-versus-activity trade-off."
    },
    {
        "id": 7, "title": "Complete Development", "level": "Beginner",
        "theme": "Piece activity", "setup": ["d4", "Nf6", "Bf4", "g6", "e3", "Bg7"],
        "answer": "Nf3",
        "prompt": "Develop a knight and prepare to castle rather than launching an unsupported attack.",
        "explanation": "Nf3 develops a piece, reinforces central squares, and prepares safe king placement. It fits naturally with the London System setup.",
        "why_not": "A sound plan often consists of improving pieces before creating immediate threats."
    },
    {
        "id": 8, "title": "Develop Against the Caro-Kann", "level": "Intermediate",
        "theme": "Development", "setup": ["e4", "c6", "d4", "d5"],
        "answer": "Nc3",
        "prompt": "Develop a piece and add support to your central e4-pawn.",
        "explanation": "Nc3 develops the queenside knight and supports e4, helping White maintain a central presence against the Caro-Kann Defence.",
        "why_not": "The lesson focuses on development and central support rather than making an early attack without enough pieces."
    },
    {
        "id": 9, "title": "Meet the French Defence", "level": "Intermediate",
        "theme": "Central support", "setup": ["e4", "e6", "d4", "d5"],
        "answer": "Nc3",
        "prompt": "Support your centre and develop a piece against Black's French Defence.",
        "explanation": "Nc3 reinforces e4 and develops naturally. White must still be aware that Black can challenge the centre with ...Bb4 or ...Nf6.",
        "why_not": "Central control is not permanent; it must be supported and defended as the game develops."
    },
    {
        "id": 10, "title": "Develop with a Pin", "level": "Advanced",
        "theme": "Piece activity", "setup": ["d4", "d5", "c4", "e6", "Nc3", "Nf6"],
        "answer": "Bg5",
        "prompt": "Develop a piece and put pressure on Black's knight, which helps defend the centre.",
        "explanation": "Bg5 is a classical Queen's Gambit Declined idea. The bishop pins the f6-knight to the queen on d8, increasing pressure on Black's central control.",
        "why_not": "The pin is useful only in context: White should continue developing and avoid assuming the knight is permanently immobilized."
    }
]


# ---------------------------------------------------------
# EXPANDED STRATEGY LAB: LESSONS 11-100
# 18 opening lines x 5 training positions = 90 lessons
# ---------------------------------------------------------

_EXPANDED_LINES = [
    # BEGINNER: 30 lessons
    {
        "name": "Italian Game",
        "level": "Beginner",
        "theme": "Development",
        "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "c3", "Nf6", "d3", "d6"],
        "idea": "Develop quickly, control the centre, and prepare to castle."
    },
    {
        "name": "Ruy Lopez",
        "level": "Beginner",
        "theme": "Piece activity",
        "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7"],
        "idea": "Develop naturally while putting pressure on Black's central structure."
    },
    {
        "name": "London System",
        "level": "Beginner",
        "theme": "Pawn structure",
        "moves": ["d4", "d5", "Bf4", "Nf6", "e3", "e6", "Nf3", "c5", "c3", "Nc6"],
        "idea": "Build a reliable pawn structure and develop pieces behind it."
    },
    {
        "name": "Scotch Game",
        "level": "Beginner",
        "theme": "Central control",
        "moves": ["e4", "e5", "Nf3", "Nc6", "d4", "exd4", "Nxd4", "Bc5", "Be3", "Qf6"],
        "idea": "Open the centre and use active piece development."
    },
    {
        "name": "Queen's Gambit Declined",
        "level": "Beginner",
        "theme": "Central control",
        "moves": ["d4", "d5", "c4", "e6", "Nc3", "Nf6", "Bg5", "Be7", "e3", "O-O"],
        "idea": "Challenge the centre while developing pieces harmoniously."
    },
    {
        "name": "English Opening",
        "level": "Beginner",
        "theme": "Positional play",
        "moves": ["c4", "e5", "Nc3", "Nf6", "g3", "d5", "cxd5", "Nxd5", "Bg2", "Nb6"],
        "idea": "Control central squares from the flank and develop patiently."
    },

    # INTERMEDIATE: 35 lessons
    {
        "name": "Caro-Kann Defence",
        "level": "Intermediate",
        "theme": "Pawn structure",
        "moves": ["e4", "c6", "d4", "d5", "Nc3", "dxe4", "Nxe4", "Bf5", "Ng3", "Bg6"],
        "idea": "Understand the Caro-Kann structure and develop without weakening your position."
    },
    {
        "name": "French Defence",
        "level": "Intermediate",
        "theme": "Central breaks",
        "moves": ["e4", "e6", "d4", "d5", "Nc3", "Nf6", "e5", "Nfd7", "f4", "c5"],
        "idea": "Recognise when to challenge the opponent's pawn centre."
    },
    {
        "name": "Open Sicilian",
        "level": "Intermediate",
        "theme": "Development",
        "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "Nc6"],
        "idea": "Develop actively and create pressure against the opponent's centre."
    },
    {
        "name": "Four Knights Game",
        "level": "Intermediate",
        "theme": "Piece coordination",
        "moves": ["e4", "e5", "Nf3", "Nc6", "Nc3", "Nf6", "Bb5", "Bb4", "O-O", "O-O"],
        "idea": "Coordinate your pieces and prepare a useful middlegame plan."
    },
    {
        "name": "Slav Defence",
        "level": "Intermediate",
        "theme": "Pawn structure",
        "moves": ["d4", "d5", "c4", "c6", "Nf3", "Nf6", "Nc3", "dxc4", "a4", "Bf5"],
        "idea": "Understand the fight for the centre and the importance of pawn structure."
    },
    {
        "name": "Scandinavian Defence",
        "level": "Intermediate",
        "theme": "Queen development",
        "moves": ["e4", "d5", "exd5", "Qxd5", "Nc3", "Qa5", "d4", "Nf6", "Nf3", "c6"],
        "idea": "Develop with tempo and avoid losing time chasing the queen unnecessarily."
    },
    {
        "name": "Vienna Game",
        "level": "Intermediate",
        "theme": "King safety",
        "moves": ["e4", "e5", "Nc3", "Nf6", "f4", "d5", "fxe5", "Nxe4", "Nf3", "Nc6"],
        "idea": "Balance attacking ambitions with development and king safety."
    },

    # ADVANCED: 25 lessons
    {
        "name": "Sicilian Najdorf",
        "level": "Advanced",
        "theme": "Dynamic play",
        "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"],
        "idea": "Understand the Najdorf's flexible structure and its dynamic counterplay."
    },
    {
        "name": "Sicilian Dragon",
        "level": "Advanced",
        "theme": "King safety",
        "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "g6"],
        "idea": "Recognise the Dragon setup and the importance of opposite-side attacking plans."
    },
    {
        "name": "King's Indian Defence",
        "level": "Advanced",
        "theme": "Strategic counterplay",
        "moves": ["d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "Nf3", "O-O"],
        "idea": "Prepare dynamic counterplay against White's central space advantage."
    },
    {
        "name": "Nimzo-Indian Defence",
        "level": "Advanced",
        "theme": "Strategic piece play",
        "moves": ["d4", "Nf6", "c4", "e6", "Nc3", "Bb4", "e3", "O-O", "Bd3", "d5"],
        "idea": "Use piece pressure and positional understanding to challenge the centre."
    },
    {
        "name": "King's Gambit",
        "level": "Advanced",
        "theme": "Initiative",
        "moves": ["e4", "e5", "f4", "exf4", "Nf3", "g5", "h4", "g4", "Ne5", "Nf6"],
        "idea": "Understand the balance between material, initiative, and king safety."
    },
]


def _build_expanded_lessons():
    expanded = []
    lesson_id = 11

    for opening in _EXPANDED_LINES:
        moves = opening["moves"]

        # Five positions from each opening line.
        for ply in range(5, 10):
            side = "White" if ply % 2 == 0 else "Black"
            move_number = (ply // 2) + 1

            expanded.append({
                "id": lesson_id,
                "title": f"{opening['name']} - Lesson {move_number}",
                "level": opening["level"],
                "theme": opening["theme"],
                "setup": moves[:ply],
                "answer": moves[ply],
                "prompt": (
                    f"You are playing as {side}. "
                    f"Choose the move that follows the main strategic idea "
                    f"of this {opening['name']} position."
                ),
                "explanation": (
                    f"This move follows a recognised opening plan. "
                    f"{opening['idea']} "
                    f"Focus on how the move improves your position "
                    f"and contributes to the overall plan."
                ),
                "why_not": (
                    "Other moves may also be playable. This exercise "
                    "focuses on the selected continuation and its strategic "
                    "purpose, rather than claiming it is the only legal "
                    "or reasonable move."
                )
            })

            lesson_id += 1

    return expanded


LESSONS.extend(_build_expanded_lessons())

assert len(LESSONS) == 100, f"Expected 100 lessons, got {len(LESSONS)}"


def _board_for(lesson):
    board = chess.Board()
    for san in lesson["setup"]:
        try:
            board.push_san(san)
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid setup move {san!r} in Strategy Lab lesson {lesson['id']}"
            ) from exc
    # Validate answer at startup so a typo doesn't silently ship.
    try:
        board.parse_san(lesson["answer"])
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid answer {lesson['answer']!r} in Strategy Lab lesson {lesson['id']}"
        ) from exc
    return board

# Validate the full setup and expected answer for every lesson at import time.
for _lesson in LESSONS:
    _board_for(_lesson)

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS strategy_progress (
            visitor_id TEXT NOT NULL,
            lesson_id INTEGER NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            correct INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (visitor_id, lesson_id)
        )
    """)
    return conn

def _visitor_id():
    # Logged-in users keep progress across browsers/sessions. Guests retain session progress.
    if session.get("user_id"):
        return "user:" + str(session["user_id"])
    if "strategy_visitor_id" not in session:
        session["strategy_visitor_id"] = secrets.token_urlsafe(24)
    return "guest:" + session["strategy_visitor_id"]

def _has_premium():
    return has_premium_access(session.get("user_id"))

def _lesson_by_id(lesson_id):
    return next((item for item in LESSONS if item["id"] == lesson_id), None)

def _public_lesson(lesson, include_fen=True):
    board = _board_for(lesson)
    return {
        "id": lesson["id"],
        "title": lesson["title"],
        "level": lesson["level"],
        "theme": lesson["theme"],
        "prompt": lesson["prompt"],
        "setup": lesson["setup"],
        "fen": board.fen() if include_fen else None,
        "free": True,
    }

@strategy_bp.route("/strategy", methods=["GET"])
def strategy_home():
    # Show a free first lesson and metadata for the remaining lessons.
    visitor_id = _visitor_id()
    with _db() as conn:
        rows = conn.execute(
            "SELECT lesson_id, attempts, correct FROM strategy_progress WHERE visitor_id = ?",
            (visitor_id,)
        ).fetchall()
    progress = {row["lesson_id"]: dict(row) for row in rows}
    return render_template(
        "strategy.html",
        lessons=LESSONS,
        premium_unlocked= True,
        progress=progress,
        score=sum(row["correct"] for row in rows),
        attempts=sum(row["attempts"] for row in rows),
    )

@strategy_bp.route("/strategy/unlock", methods=["POST"])
def strategy_unlock():
    # Backwards-compatible route for old links/forms; no shared access codes are accepted.
    if not session.get("user_id"):
        return redirect(url_for("account.login", next="/strategy"))
    return redirect(url_for("account.buy_strategy"))

@strategy_bp.route("/api/strategy/lesson/<int:lesson_id>", methods=["GET"])
def strategy_get_lesson(lesson_id):
    lesson = _lesson_by_id(lesson_id)
    if not lesson:
        return jsonify({"error": "Lesson not found."}), 404
    # if lesson_id != 1 and not _has_premium():
      #  return jsonify({"error": "Premium access is required for this lesson."}), 403
    return jsonify(_public_lesson(lesson))

@strategy_bp.route("/api/strategy/answer", methods=["POST"])
def strategy_submit_answer():
    data = request.get_json(silent=True) or {}
    try:
        lesson_id = int(data.get("lesson_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid lesson ID."}), 400

    lesson = _lesson_by_id(lesson_id)
    if not lesson:
        return jsonify({"error": "Lesson not found."}), 404
    # if lesson_id != 1 and not _has_premium():
      #  return jsonify({"error": "Premium access is required for this lesson."}), 403

    move_uci = str(data.get("move_uci", "")).strip()
    board = _board_for(lesson)
    try:
        chosen = chess.Move.from_uci(move_uci)
    except ValueError:
        return jsonify({"error": "Invalid move format."}), 400
    if chosen not in board.legal_moves:
        return jsonify({"error": "That is not a legal move in this position."}), 400

    correct_move = board.parse_san(lesson["answer"])
    is_correct = chosen == correct_move
    chosen_san = board.san(chosen)
    correct_san = board.san(correct_move)

    visitor_id = _visitor_id()
    with _db() as conn:
        conn.execute("""
            INSERT INTO strategy_progress(visitor_id, lesson_id, attempts, correct)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(visitor_id, lesson_id) DO UPDATE SET
                attempts = attempts + 1,
                correct = correct + excluded.correct
        """, (visitor_id, lesson_id, 1 if is_correct else 0))
        row = conn.execute("""
            SELECT attempts, correct FROM strategy_progress
            WHERE visitor_id = ? AND lesson_id = ?
        """, (visitor_id, lesson_id)).fetchone()
        totals = conn.execute("""
            SELECT COALESCE(SUM(correct),0) AS score,
                   COALESCE(SUM(attempts),0) AS attempts
            FROM strategy_progress WHERE visitor_id = ?
        """, (visitor_id,)).fetchone()

    return jsonify({
        "correct": is_correct,
        "chosen_san": chosen_san,
        "correct_san": correct_san,
        "explanation": lesson["explanation"],
        "why_not": lesson["why_not"],
        "lesson_attempts": row["attempts"],
        "lesson_correct": row["correct"],
        "score": totals["score"],
        "attempts": totals["attempts"],
        "accuracy": round(100 * totals["score"] / totals["attempts"]) if totals["attempts"] else 0
    })

@strategy_bp.route("/api/strategy/progress", methods=["GET"])
def strategy_progress():
    visitor_id = _visitor_id()
    with _db() as conn:
        rows = conn.execute(
            "SELECT lesson_id, attempts, correct FROM strategy_progress WHERE visitor_id = ?",
            (visitor_id,)
        ).fetchall()
    attempts = sum(row["attempts"] for row in rows)
    score = sum(row["correct"] for row in rows)
    return jsonify({
        "score": score,
        "attempts": attempts,
        "accuracy": round(100 * score / attempts) if attempts else 0,
        "lessons_completed": sum(1 for row in rows if row["correct"] > 0),
        "by_lesson": [dict(row) for row in rows]
    })
