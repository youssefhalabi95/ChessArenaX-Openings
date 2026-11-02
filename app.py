
from flask import Flask, render_template, jsonify, request
import chess
import requests
import json
import random
import os

app = Flask(__name__)

app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    )
if not app.config["SECRET_KEY"]:
        raise RuntimeError("Set the SECRET_KEY environment variable before starting ChessArenaX.")

from auth_payment import account_bp, init_account_db
from strategy_room import strategy_bp

app.register_blueprint(account_bp)
app.register_blueprint(strategy_bp)

init_account_db()

# IMPORTANT:
# Paste your COMPLETE existing OPENINGS = [...] list here,
# unchanged, from your Opening Trainer app.py.
#
# Each opening should retain:
# slug, name, side, description, variations
# Each variation should retain:
# name, plan, moves

OPENINGS = [
    {
        "slug": "trompowsky",
        "name": "Trompowsky Attack",
        "side": "white",
        "description": "Challenge Black's knight early with Bg5 and build a flexible centre.",
        "variations": [
            {
                "name": "Main Line",
                "plan": "Develop actively, control the centre, and castle safely.",
                "moves": "d4 Nf6 Bg5 Ne4 Bf4 d5 e3 c5 Nd2 Nxd2 Qxd2 Nc6 Nf3 e6 c3 Bd6"
            },
            {
                "name": "Against ...d5",
                "plan": "Exchange the knight when useful and use your central space.",
                "moves": "d4 Nf6 Bg5 d5 Bxf6 exf6 e3 Bd6 c4 dxc4 Bxc4 O-O Nc3"
            },
            {
                "name": "Flexible ...c5 Counterplay",
                "plan": "Meet White's central setup with ...c5, develop safely, and keep the position flexible.",
                "moves": "d4 Nf6 Bg5 Ne4 Bh4 c5 f3 Qa5+ c3 Nf6 Nd2 cxd4 Nb3 Qh5 Bf2"
            }
        ]
    },
    {
        "slug": "kings-gambit",
        "name": "King's Gambit",
        "side": "white",
        "description": "Sacrifice the f-pawn for rapid development and attacking chances.",
        "variations": [
            {
                "name": "King's Gambit Accepted",
                "plan": "Develop quickly and challenge Black's kingside pawn chain.",
                "moves": "e4 e5 f4 exf4 Nf3 g5 h4 g4 Ne5 Nf6 d4 d6 Nd3"
            },
            {
                "name": "Falkbeer Countergambit",
                "plan": "Open the centre carefully and avoid falling behind in development.",
                "moves": "e4 e5 f4 d5 exd5 e4 d3 Nf6 dxe4 Nxe4 Nf3"
            },
            {
                "name": "Classical Declined Setup",
                "plan": "If Black declines the pawn, develop rapidly, keep the centre under pressure, and castle before launching an attack.",
                "moves": "e4 e5 f4 Bc5 Nf3 d6 Nc3 Nf6 Bc4 Nc6 d3 O-O Qe2"
            }
        ]
    },
    {
        "slug": "danish-gambit",
        "name": "Danish Gambit",
        "side": "white",
        "description": "Offer pawns for open diagonals and quick attacking development.",
        "variations": [
            {
                "name": "Accepted Gambit",
                "plan": "Use your bishops and rapid development to compensate for the pawns.",
                "moves": "e4 e5 d4 exd4 c3 dxc3 Bc4 cxb2 Bxb2 Nf6 Nc3 Bb4"
            },
            {
                "name": "Declined with ...d5",
                "plan": "Keep the centre active and develop your pieces naturally.",
                "moves": "e4 e5 d4 exd4 c3 d5 exd5 Qxd5 cxd4 Nc6 Nf3"
            },
            {
                "name": "Danish Gambit Declined",
                "plan": "If Black holds the centre, use c3 and d4 to challenge it, then develop without forcing the sacrifice.",
                "moves": "e4 e5 d4 exd4 c3 d5 exd5 Qxd5 cxd4 Nc6 Nf3 Bg4 Nc3 Bb4"
            }
        ]
    },
    {
        "slug": "italian-game",
        "name": "Italian Game",
        "side": "white",
        "description": "Develop naturally, castle, and apply pressure near Black's f7-square.",
        "variations": [
            {
                "name": "Giuoco Piano",
                "plan": "Prepare d4 with support from your pieces.",
                "moves": "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O O-O"
            },
            {
                "name": "Two Knights Defence",
                "plan": "Develop quickly and contest the centre.",
                "moves": "e4 e5 Nf3 Nc6 Bc4 Nf6 d3 Bc5 O-O d6 c3 O-O"
            },
            {
                "name": "Evans Gambit",
                "plan": "Gain tempi by offering the b-pawn, then use c3 and d4 to build a strong centre and open lines.",
                "moves": "e4 e5 Nf3 Nc6 Bc4 Bc5 b4 Bxb4 c3 Ba5 d4 exd4 O-O"
            }
        ]
    },
    {
        "slug": "london-system",
        "name": "London System",
        "side": "white",
        "description": "Build a dependable setup with d4, Bf4, e3, and Nf3.",
        "variations": [
            {
                "name": "Classic Setup",
                "plan": "Complete development before choosing a central or kingside plan.",
                "moves": "d4 d5 Bf4 Nf6 e3 e6 Nf3 Bd6 Bg3 O-O Bd3 c5"
            },
            {
                "name": "Against ...g6",
                "plan": "Keep the bishop active and build a solid pawn centre.",
                "moves": "d4 Nf6 Bf4 g6 e3 Bg7 Nf3 O-O Be2 d6 O-O"
            },
            {
                "name": "London vs King's Fianchetto",
                "plan": "Develop behind a stable pawn structure, then challenge Black's centre with c3 and keep the dark-squared bishop active.",
                "moves": "d4 Nf6 Bf4 g6 e3 Bg7 h3 O-O Nf3 d6 Be2 c5 c3"
            }
        ]
    },
    {
        "slug": "ruy-lopez",
        "name": "Ruy Lopez",
        "side": "white",
        "description": "Put long-term pressure on Black's knight and develop harmoniously.",
        "variations": [
            {
                "name": "Morphy Defence",
                "plan": "Castle, develop the rook, and prepare to challenge the centre.",
                "moves": "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5"
            },
            {
                "name": "Exchange Variation",
                "plan": "Trade bishop for knight and aim to use the resulting pawn structure.",
                "moves": "e4 e5 Nf3 Nc6 Bb5 a6 Bxc6 dxc6 O-O f6 d4"
            },
            {
                "name": "Open Ruy Lopez",
                "plan": "After ...Nxe4, use d4 to gain central space and develop with tempo while Black's knight is exposed.",
                "moves": "e4 e5 Nf3 Nc6 Bb5 Nf6 O-O Nxe4 d4 Nd6 Bxc6 dxc6 dxe5"
            }
        ]
    },
    {
        "slug": "queens-gambit",
        "name": "Queen's Gambit",
        "side": "white",
        "description": "Challenge Black's d-pawn and fight for central control.",
        "variations": [
            {
                "name": "Queen's Gambit Declined",
                "plan": "Develop behind a stable centre and prepare pressure against d5.",
                "moves": "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O Nf3"
            },
            {
                "name": "Queen's Gambit Accepted",
                "plan": "Use development and central control as compensation for the c-pawn.",
                "moves": "d4 d5 c4 dxc4 e3 Nf6 Bxc4 e6 Nf3 c5 O-O"
            },
            {
                "name": "Slav Defence",
                "plan": "Support the d-pawn with ...c6, develop the queenside, and avoid weakening the centre unnecessarily.",
                "moves": "d4 d5 c4 c6 Nf3 Nf6 Nc3 e6 Bg5 Be7 e3 O-O"
            }
        ]
    },
    {
        "slug": "vienna-game",
        "name": "Vienna Game",
        "side": "white",
        "description": "A flexible opening with both positional and attacking possibilities.",
        "variations": [
            {
                "name": "Vienna Game",
                "plan": "Develop the bishop and prepare a central advance.",
                "moves": "e4 e5 Nc3 Nf6 g3 d5 exd5 Nxd5 Bg2 Be6 Nf3"
            },
            {
                "name": "Vienna Gambit",
                "plan": "Use f4 to challenge Black's centre and open attacking lines.",
                "moves": "e4 e5 Nc3 Nf6 f4 d5 fxe5 Nxe4 Nf3 Be7 d3"
            },
            {
                "name": "Vienna Gambit Accepted",
                "plan": "Use f4 to challenge e5, then build a centre and develop quickly if Black accepts the pawn.",
                "moves": "e4 e5 Nc3 Nc6 f4 exf4 Nf3 g5 d4 g4 Bxf4"
            }
        ]
    },
    {
        "slug": "reti-opening",
        "name": "Réti Opening",
        "side": "white",
        "description": "Control the centre from the flanks before striking with central pawns.",
        "variations": [
            {
                "name": "King's Indian Attack Setup",
                "plan": "Fianchetto your bishop and keep the centre flexible.",
                "moves": "Nf3 d5 c4 e6 g3 Nf6 Bg2 Be7 O-O O-O d3"
            },
            {
                "name": "Symmetrical Réti",
                "plan": "Develop naturally and prepare a timely central break.",
                "moves": "Nf3 Nf6 c4 c5 g3 g6 Bg2 Bg7 O-O O-O Nc3"
            },
            {
                "name": "Réti: Space-Gaining Line",
                "plan": "Use the flank pawns to gain space while keeping central options flexible; meet ...d4 by challenging it.",
                "moves": "Nf3 d5 c4 d4 b4 c5 e3 Nf6 exd4 cxd4 Bb2"
            }
        ]
    },
    {
        "slug": "four-knights",
        "name": "Four Knights Game",
        "side": "white",
        "description": "Develop both knights and contest the centre using classical principles.",
        "variations": [
            {
                "name": "Spanish Four Knights",
                "plan": "Develop with tempo and prepare to castle.",
                "moves": "e4 e5 Nf3 Nc6 Nc3 Nf6 Bb5 Bb4 O-O O-O d3"
            },
            {
                "name": "Scotch Four Knights",
                "plan": "Open the centre when your development supports active play.",
                "moves": "e4 e5 Nf3 Nc6 Nc3 Nf6 d4 exd4 Nxd4 Bb4"
            },
            {
                "name": "Scotch Four Knights: Exchange",
                "plan": "Open the centre with d4, recapture with a piece, and decide whether to exchange or maintain central tension.",
                "moves": "e4 e5 Nf3 Nc6 Nc3 Nf6 d4 exd4 Nxd4 Bb4 Nxc6 bxc6"
            }
        ]
    },
    {
        "slug": "sicilian-defense",
        "name": "Sicilian Defense",
        "side": "black",
        "description": "Answer 1.e4 with ...c5 and fight for the centre asymmetrically.",
        "variations": [
            {
                "name": "Open Sicilian: ...d6",
                "plan": "Challenge White's centre and prepare queenside counterplay.",
                "moves": "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Be3 e6"
            },
            {
                "name": "Classical Setup",
                "plan": "Develop actively and prepare central counterplay.",
                "moves": "e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 d6 Be2 e6"
            },
            {
                "name": "Dragon Setup",
                "plan": "Fianchetto the bishop, castle, and use the semi-open c-file plus central breaks for counterplay.",
                "moves": "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6 Be3 Bg7 f3 O-O"
            }
        ]
    },
    {
        "slug": "caro-kann",
        "name": "Caro-Kann Defense",
        "side": "black",
        "description": "Support ...d5 with ...c6 and aim for a sound pawn structure.",
        "variations": [
            {
                "name": "Classical Variation",
                "plan": "Develop the light-squared bishop before playing ...e6.",
                "moves": "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Bf5 Ng3 Bg6 Nf3"
            },
            {
                "name": "Advance Variation",
                "plan": "Attack White's pawn chain with ...c5.",
                "moves": "e4 c6 d4 d5 e5 Bf5 Nf3 e6 Be2 c5 O-O"
            },
            {
                "name": "Advance Variation: ...c5",
                "plan": "Challenge White's space with ...c5 while developing pieces and keeping the king safe.",
                "moves": "e4 c6 d4 d5 e5 Bf5 Nc3 e6 g4 Bg6 Nge2 c5"
            }
        ]
    },
    {
        "slug": "scandinavian-defense",
        "name": "Scandinavian Defense",
        "side": "black",
        "description": "Challenge White's e-pawn immediately with ...d5.",
        "variations": [
            {
                "name": "Main Line: ...Qxd5",
                "plan": "Recover the pawn and develop while avoiding unnecessary queen moves.",
                "moves": "e4 d5 exd5 Qxd5 Nc3 Qa5 d4 Nf6 Nf3 c6"
            },
            {
                "name": "Modern ...Nf6",
                "plan": "Develop a piece first and recapture the pawn with a piece.",
                "moves": "e4 d5 exd5 Nf6 d4 Nxd5 Nf3 g6 Be2 Bg7 O-O"
            },
            {
                "name": "Modern Queen Retreat",
                "plan": "Retreat the queen to a useful square, then develop normally and prepare ...c6 or ...e6.",
                "moves": "e4 d5 exd5 Qxd5 Nc3 Qd6 d4 Nf6 Nf3 c6 Bc4 Bf5"
            }
        ]
    },
    {
        "slug": "pirc-defense",
        "name": "Pirc Defense",
        "side": "black",
        "description": "Allow White a broad centre, then attack it with pieces and pawn breaks.",
        "variations": [
            {
                "name": "Classical System",
                "plan": "Fianchetto the bishop and pressure White's central pawns.",
                "moves": "e4 d6 d4 Nf6 Nc3 g6 Nf3 Bg7 Be2 O-O O-O"
            },
            {
                "name": "Austrian Attack",
                "plan": "Challenge White's centre with a timely ...c5 or ...e5.",
                "moves": "e4 d6 d4 Nf6 Nc3 g6 f4 Bg7 Nf3 O-O Bd3"
            },
            {
                "name": "Austrian Attack: Central Counter",
                "plan": "Allow White a broad centre, then undermine it with ...c5 and ...e6 rather than passively defending.",
                "moves": "e4 d6 d4 Nf6 Nc3 g6 f4 Bg7 Nf3 O-O Bd3 c5 d5 e6"
            }
        ]
    },
    {
        "slug": "modern-defense",
        "name": "Modern Defense",
        "side": "black",
        "description": "Fianchetto the bishop and keep the central pawn structure flexible.",
        "variations": [
            {
                "name": "Robatsch Setup",
                "plan": "Invite White forward, then attack the centre.",
                "moves": "e4 g6 d4 Bg7 Nc3 d6 Nf3 a6 Be2 b5 O-O"
            },
            {
                "name": "Against 1.d4",
                "plan": "Develop the bishop and prepare a later central counterstrike.",
                "moves": "d4 g6 c4 Bg7 Nc3 d6 e4 Nc6 Be3 e5 d5"
            },
            {
                "name": "Modern: Queenside Expansion",
                "plan": "Fianchetto first, then use ...a6 and ...b5 for queenside space while retaining central flexibility.",
                "moves": "e4 g6 d4 Bg7 Nc3 d6 Be3 a6 Qd2 b5 O-O-O Nd7"
            }
        ]
    },
    {
        "slug": "kings-indian-defense",
        "name": "King's Indian Defense",
        "side": "black",
        "description": "Fianchetto the bishop and counterattack White's centre.",
        "variations": [
            {
                "name": "Classical Setup",
                "plan": "Finish development and prepare the central break ...e5.",
                "moves": "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5"
            },
            {
                "name": "Fianchetto Variation",
                "plan": "Develop harmoniously and maintain pressure on the centre.",
                "moves": "d4 Nf6 c4 g6 Nf3 Bg7 g3 O-O Bg2 d6 O-O"
            },
            {
                "name": "Sämisch-Style Centre",
                "plan": "Complete development and use ...e5 to challenge the centre; after d5, seek queenside counterplay.",
                "moves": "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 e5 d5"
            }
        ]
    },
    {
        "slug": "queens-indian-defense",
        "name": "Queen's Indian Defense",
        "side": "black",
        "description": "Use ...b6 and ...Bb7 to control central squares from a distance.",
        "variations": [
            {
                "name": "Classical Setup",
                "plan": "Fianchetto the queen's bishop and contest the centre.",
                "moves": "d4 Nf6 c4 e6 Nf3 b6 g3 Bb7 Bg2 Be7 O-O O-O"
            },
            {
                "name": "Petrosian-Style Setup",
                "plan": "Keep the centre stable and use piece pressure to restrict White.",
                "moves": "d4 Nf6 c4 e6 Nf3 b6 a3 Bb7 Nc3 d5 cxd5 Nxd5"
            },
            {
                "name": "Queen's Indian: ...Ne4",
                "plan": "Use the fianchettoed bishop to influence the centre and place a knight actively on e4 when possible.",
                "moves": "d4 Nf6 c4 e6 Nf3 b6 g3 Bb7 Bg2 Be7 O-O O-O Nc3 Ne4"
            }
        ]
    },
    {
        "slug": "dutch-defense",
        "name": "Dutch Defense",
        "side": "black",
        "description": "Play ...f5 to control e4 and create kingside attacking chances.",
        "variations": [
            {
                "name": "Classical Dutch",
                "plan": "Support your kingside space and complete development.",
                "moves": "d4 f5 c4 Nf6 g3 e6 Bg2 Be7 Nf3 O-O O-O"
            },
            {
                "name": "Leningrad Setup",
                "plan": "Fianchetto the bishop and combine kingside space with central play.",
                "moves": "d4 f5 c4 Nf6 g3 g6 Bg2 Bg7 Nf3 O-O O-O"
            },
            {
                "name": "Dutch: Classical Setup",
                "plan": "Control e4 with ...f5, finish development, and prepare a central or kingside pawn break.",
                "moves": "d4 f5 g3 Nf6 Bg2 e6 Nf3 Be7 O-O O-O c4 d6 Nc3"
            }
        ]
    },
    {
        "slug": "english-symmetrical-defense",
        "name": "English Defense — Symmetrical Variation",
        "side": "black",
        "description": "Meet 1.c4 with ...c5 and mirror White's flank-pawn strategy.",
        "variations": [
            {
                "name": "Symmetrical English",
                "plan": "Develop both knights and keep control of central squares.",
                "moves": "c4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7 Nf3 Nf6 O-O O-O"
            },
            {
                "name": "Four Knights Setup",
                "plan": "Develop before deciding on a central pawn break.",
                "moves": "c4 c5 Nf3 Nf6 Nc3 Nc6 g3 g6 Bg2 Bg7 O-O"
            },
            {
                "name": "Symmetrical English: ...d5 Break",
                "plan": "Mirror White's flank setup, develop efficiently, and look for a timely central break rather than passively copying.",
                "moves": "c4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7 Nf3 Nf6 O-O O-O d3"
            }
        ]
    },
    {
        "slug": "budapest-defense",
        "name": "Budapest Gambit",
        "side": "black",
        "description": "Respond to 1.d4 and 2.c4 with ...e5, offering a pawn for active play.",
        "variations": [
            {
                "name": "Main Line: ...Ng4",
                "plan": "Use active piece development to compensate for the pawn.",
                "moves": "d4 Nf6 c4 e5 dxe5 Ng4 Nf3 Nc6 Bf4 Bb4+ Nbd2"
            },
            {
                "name": "Early ...Bb4+",
                "plan": "Use the check to disrupt White's development and create active play.",
                "moves": "d4 Nf6 c4 e5 dxe5 Ng4 Nf3 Bb4+ Bd2 Nc6"
            },
            {
                "name": "Budapest: Main Development",
                "plan": "After sacrificing the e-pawn, develop with tempo and use active pieces to compensate for the pawn.",
                "moves": "d4 Nf6 c4 e5 dxe5 Ng4 Nf3 Nc6 Bf4 Bb4+ Nbd2 Qe7"
            }
        ]
    }
]


# -------------------------
# Opening Trainer functions
# -------------------------

def explain_opening_move(san, ply, opening_name, plan):
    """Basic move explanation; replace with your original function if preferred."""
    move_number = (ply + 2) // 2
    side = "White" if ply % 2 == 0 else "Black"

    return (
        f"{side}'s move {san} in the {opening_name}. "
        f"Follow the plan: {plan} "
        "Consider the move's effect on development, the center, king safety, "
        "and the opponent's possible replies."
    )


@app.route("/")
def home():
    white_openings = [o for o in OPENINGS if o.get("side", "").lower() == "white"]
    black_openings = [o for o in OPENINGS if o.get("side", "").lower() == "black"]

    return render_template(
        "index.html",
        white_openings=white_openings,
        black_openings=black_openings,
        opening_count=len(OPENINGS),
        variation_count=sum(len(o.get("variations", [])) for o in OPENINGS)
    )


@app.route("/openings")
def openings_home():
    white_openings = [
        o for o in OPENINGS
        if o.get("side", "").lower() == "white"
    ]
    black_openings = [
        o for o in OPENINGS
        if o.get("side", "").lower() == "black"
    ]

    return render_template(
        "openings.html",
        white_openings=white_openings,
        black_openings=black_openings
    )


@app.route("/opening/<slug>")
def opening_page(slug):
    opening = next((o for o in OPENINGS if o["slug"] == slug), None)

    if opening is None:
        return "Opening not found", 404

    explained_variations = []

    for variation in opening.get("variations", []):
        moves = variation.get("moves", [])
        if isinstance(moves, str):
            moves = moves.split()
        explained_moves = []

        for ply, san in enumerate(moves):
            explained_moves.append({
                "san": san,
                "explanation": explain_opening_move(
                    san,
                    ply,
                    opening["name"],
                    variation.get("plan", opening.get("description", "Develop your pieces."))
                )
            })

        explained_variations.append({
            **variation,
            # The browser trainer expects an array of SAN moves, not one string.
            "moves": moves,
            "explained_moves": explained_moves
        })

    # opening.html reads its lines from opening.variations, so include
    # the enriched variations here to restore the move-by-move explanations.
    opening_for_template = {
        **opening,
        "variations": explained_variations
    }

    return render_template(
        "opening.html",
        opening=opening_for_template
    )


# -------------------------
# Tactics Trainer functions
# -------------------------

PUZZLE_URL = (
    "https://raw.githubusercontent.com/"
    "mcognetta/lichess-combined-puzzle-game-db/"
    "main/combined_puzzle_db_first_100.ndjson"
)

PUZZLES = []
LOAD_ERROR = None


def load_puzzles():
    global PUZZLES, LOAD_ERROR

    try:
        response = requests.get(PUZZLE_URL, timeout=30)
        response.raise_for_status()

        valid = []

        for line in response.text.splitlines():
            try:
                record = json.loads(line)
                data = record.get("puzzle", {})
                original_fen = data.get("FEN")
                raw_moves = data.get("Moves", "").split()

                if not original_fen or len(raw_moves) < 2:
                    continue

                board = chess.Board(original_fen)

                # Validate the complete line.
                for uci in raw_moves:
                    move = chess.Move.from_uci(uci)
                    if move not in board.legal_moves:
                        raise ValueError("Illegal puzzle move")
                    board.push(move)

                # The FEN is before the opponent's preceding move.
                start_board = chess.Board(original_fen)
                first_move = chess.Move.from_uci(raw_moves[0])

                if first_move not in start_board.legal_moves:
                    continue

                start_board.push(first_move)
                solution = raw_moves[1:]

                # Validate the solution from the puzzle's start position.
                check_board = start_board.copy()

                for uci in solution:
                    move = chess.Move.from_uci(uci)
                    if move not in check_board.legal_moves:
                        raise ValueError("Illegal solution move")
                    check_board.push(move)

                valid.append({
                    "id": str(data.get("PuzzleId", len(valid) + 1)),
                    "fen": start_board.fen(),
                    "moves": solution,
                    "rating": int(data.get("Rating") or 1200),
                    "themes": data.get("Themes", ""),
                    "url": data.get("GameUrl", "")
                })

            except (ValueError, TypeError, KeyError):
                continue

        if not valid:
            raise ValueError("No valid puzzles were loaded.")

        PUZZLES = valid
        LOAD_ERROR = None

    except Exception as exc:
        PUZZLES = []
        LOAD_ERROR = str(exc)


def explain_tactics_move(board, move):
    san = board.san(move)
    piece = board.piece_at(move.from_square)

    piece_names = {
        chess.PAWN: "pawn",
        chess.KNIGHT: "knight",
        chess.BISHOP: "bishop",
        chess.ROOK: "rook",
        chess.QUEEN: "queen",
        chess.KING: "king"
    }

    piece_name = piece_names.get(piece.piece_type, "piece") if piece else "piece"
    parts = []

    if board.is_capture(move):
        parts.append("captures material")
    else:
        parts.append("moves to a new square")

    if board.gives_check(move):
        parts.append("gives check")

    if move.promotion:
        parts.append("promotes")

    return (
        f"{san}: the {piece_name} {', '.join(parts)}. "
        "Look at the opponent's forcing replies and the threats created."
    )


def puzzle_by_id(puzzle_id):
    return next((p for p in PUZZLES if p["id"] == puzzle_id), None)


@app.route("/tactics")
def tactics_home():
    return render_template("tactics.html")

# ============================================================
# CHESSARENA X STRATEGY LAB
# ============================================================

@app.route("/strategy")
def strategy_home():
    return render_template("strategy.html")


@app.route("/api/status")
def api_status():
    return jsonify({
        "count": len(PUZZLES),
        "error": LOAD_ERROR
    })


@app.route("/api/puzzle")
def api_puzzle():
    if not PUZZLES:
        return jsonify({
            "error": "The puzzle library is unavailable. Check the server logs and try again."
        }), 503

    difficulty = request.args.get("difficulty", "all")
    theme = request.args.get("theme", "all").lower()
    excluded = set(request.args.get("exclude", "").split(","))

    selected = [p for p in PUZZLES if p["id"] not in excluded]

    if difficulty == "beginner":
        selected = [p for p in selected if p["rating"] < 1400]
    elif difficulty == "intermediate":
        selected = [p for p in selected if 1400 <= p["rating"] < 1900]
    elif difficulty == "advanced":
        selected = [p for p in selected if p["rating"] >= 1900]

    theme_aliases = {
        "fork": ["fork"],
        "pin": ["pin"],
        "skewer": ["skewer"],
        "mate": ["mate"],
        "discovered": ["discoveredattack", "discovered"],
        "sacrifice": ["sacrifice"],
        "endgame": ["endgame"]
    }

    if theme != "all":
        terms = theme_aliases.get(theme, [theme])
        selected = [
            p for p in selected
            if any(term in p["themes"].lower().replace(" ", "") for term in terms)
        ]

    if not selected:
        return jsonify({
            "error": "No puzzles match those filters. Try another theme or difficulty."
        }), 404

    puzzle = random.choice(selected)

    return jsonify({
        "id": puzzle["id"],
        "fen": puzzle["fen"],
        "rating": puzzle["rating"],
        "themes": puzzle["themes"],
        "total": len(PUZZLES),
        "source": puzzle["url"]
    })


@app.route("/api/solution/<puzzle_id>")
def api_solution(puzzle_id):
    puzzle = puzzle_by_id(puzzle_id)

    if puzzle is None:
        return jsonify({"error": "Puzzle not found"}), 404

    board = chess.Board(puzzle["fen"])
    moves = []

    for uci in puzzle["moves"]:
        move = chess.Move.from_uci(uci)

        if move not in board.legal_moves:
            return jsonify({"error": "Puzzle solution failed validation"}), 500

        moves.append({
            "uci": uci,
            "san": board.san(move),
            "color": "white" if board.turn == chess.WHITE else "black",
            "explanation": explain_tactics_move(board, move)
        })

        board.push(move)

    return jsonify({"moves": moves})


@app.errorhandler(404)
def not_found(_error):
    # Preserve JSON responses for the API.
    from flask import jsonify
    return jsonify({"error": "Page not found"}), 404


# Load the puzzle library when the app starts.
load_puzzles()


if __name__ == "__main__":
    app.run(debug=True)
