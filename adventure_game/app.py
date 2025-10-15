from __future__ import annotations

import os
import logging
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from .core.game_engine import GameEngine


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "configs" / "vn_horror_short.yaml"
DB_PATH = BASE_DIR / "game_state.db"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(level=LOG_LEVEL)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

_engine: GameEngine | None = None


def get_engine() -> GameEngine:
    global _engine
    if _engine is None:
        provider_override = os.getenv("ADVENTURE_PROVIDER")
        _engine = GameEngine(
            config_path=CONFIG_PATH,
            db_path=DB_PATH,
            provider=provider_override,
        )
    return _engine


@app.route("/", methods=["GET", "POST"])
def game() -> str:
    engine = get_engine()
    narration = None
    if request.method == "POST":
        player_input = request.form.get("player_input", "").strip()
        if not player_input:
            flash("Please enter an action.", "warning")
            return redirect(url_for("game"))
        try:
            result = engine.process_turn(player_input)
            narration = result["narration"]
        except ValueError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("game"))
        except RuntimeError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("game"))

    ui_state = engine.get_ui_state()
    if narration is None and ui_state["log"]:
        narration = ui_state["log"][-1]["narrator"]

    return render_template(
        "game.html",
        narration=narration,
        stats=ui_state["stats"],
        inventory=ui_state["inventory"],
        npc_rel=ui_state["npc_rel"],
        log=ui_state["log"],
        summary=ui_state["summary"],
        tokens=ui_state["tokens"],
    )


@app.route("/reset", methods=["POST"])
def reset() -> str:
    global _engine
    _engine = None
    flash("Game reset. Fresh mysteries await.", "info")
    return redirect(url_for("game"))


if __name__ == "__main__":
    app.run(debug=True)
