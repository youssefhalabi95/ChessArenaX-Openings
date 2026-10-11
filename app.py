from flask import Flask, render_template, abort
import re

app = Flask(__name__)

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


def explain_move(san, ply, opening_name, plan):
    """Explain the likely purpose of each move in the context of the opening."""
    side = "White" if ply % 2 == 0 else "Black"

    if san in ("O-O", "O-O-O"):
        castle = "kingside" if san == "O-O" else "queenside"
        return (
            f"{side} castles {castle}: the king moves toward safety and the rook "
            f"joins the game. This supports the broader plan of {plan.lower()}"
        )

    check = "+" in san
    mate = "#" in san
    capture = "x" in san
    clean = san.replace("+", "").replace("#", "").replace("!", "").replace("?", "")
    dest_match = re.search(r"([a-h][1-8])$", clean)
    destination = dest_match.group(1) if dest_match else None

    piece_char = clean[0] if clean and clean[0] in "KQRBN" else "P"
    piece_names = {
        "K": "king",
        "Q": "queen",
        "R": "rook",
        "B": "bishop",
        "N": "knight",
        "P": "pawn"
    }
    piece = piece_names[piece_char]

    if mate:
        reason = "delivers checkmate and ends the game"
    elif check:
        reason = "gives check, forcing the opponent to answer the immediate king threat"
    elif capture:
        reason = "captures material or removes a defender, changing the tactical balance"
    elif piece_char == "P":
        if destination in ("e4", "e5", "d4", "d5", "c4", "c5"):
            reason = (
                f"occupies or challenges the centre on {destination}, gaining space "
                "and influencing key squares"
            )
        elif destination in ("f4", "f5", "g4", "g5", "h4", "h5"):
            reason = (
                f"advances a kingside pawn to gain space or prepare an attacking plan "
                f"on {destination}"
            )
        elif destination in ("a4", "a5", "b4", "b5", "c4", "c5"):
            reason = (
                f"uses a queenside pawn to gain space or challenge the opponent's "
                f"pawn structure on {destination}"
            )
        else:
            reason = (
                f"advances a pawn to {destination or 'a new square'}, supporting the "
                "position or preparing a pawn break"
            )
    elif piece_char == "N":
        reason = (
            f"develops or repositions the knight to {destination or 'an active square'}, "
            "where it can pressure central squares and support other pieces"
        )
    elif piece_char == "B":
        reason = (
            f"develops or repositions the bishop to {destination or 'an active diagonal'}, "
            "improving its influence over long diagonals"
        )
    elif piece_char == "R":
        reason = (
            f"activates the rook toward {destination or 'an open line'}, "
            "where it can support files and connected pieces"
        )
    elif piece_char == "Q":
        reason = (
            f"places the queen on {destination or 'a useful square'}; the idea is to "
            "support the position without losing time to repeated queen moves"
        )
    else:
        reason = (
            f"improves the {piece}'s placement toward "
            f"{destination or 'a safer square'}"
        )

    extra = f" The move also fits the {opening_name} plan: {plan}"
    if check:
        extra += " Keep in mind that a check is useful only if it improves the position."

    return f"{side} {reason}.{extra}"


@app.route("/")
def home():
    white_openings = [
        opening for opening in OPENINGS if opening["side"] == "white"
    ]
    black_openings = [
        opening for opening in OPENINGS if opening["side"] == "black"
    ]
    return render_template(
        "index.html",
        white_openings=white_openings,
        black_openings=black_openings
    )


@app.route("/opening/<slug>")
def opening_page(slug):
    opening = next(
        (item for item in OPENINGS if item["slug"] == slug),
        None
    )

    if opening is None:
        abort(404)

    page_data = dict(opening)
    page_data["variations"] = []

    for variation in opening["variations"]:
        moves = variation["moves"].split()
        explained_moves = [
            {
                "san": san,
                "explanation": explain_move(
                    san, index, opening["name"], variation["plan"]
                )
            }
            for index, san in enumerate(moves)
        ]

        page_data["variations"].append({
            "name": variation["name"],
            "plan": variation["plan"],
            "moves": moves,
            "explained_moves": explained_moves
        })

    return render_template("opening.html", opening=page_data)


@app.errorhandler(404)
def not_found(_error):
    return (
        "Opening not found. Return to the homepage to choose another opening.",
        404
    )


if __name__ == "__main__":
    app.run(debug=True)