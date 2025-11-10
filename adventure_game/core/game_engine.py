from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml
import json

from . import prompts
from .llm_provider import base as provider_base
from .summarizer import LogSummarizer
from ..models.db_models import GameStateRepository
from ..utils.token_counter import count_tokens


class GameEngine:
    def __init__(
        self,
        *,
        config_path: Path,
        db_path: Path,
        provider: str | None = None,
        slot: str = "default",
    ) -> None:
        self.config_path = config_path
        self.db_path = db_path
        self.slot = slot

        self.config = self._load_config()
        self.hidden_lore = self.config.get("lore_seed", "The world holds secrets.")

        narrator_provider = self.config["models"]["narrator"]["provider"]
        lore_provider = self.config["models"]["lore_generator"]["provider"]
        summary_provider = self.config["models"]["summarizer"]["provider"]

        self.narrator = self._instantiate_provider(narrator_provider, "narrator")
        self.lore_generator = self._instantiate_provider(lore_provider, "lore_generator")

        self.repository = GameStateRepository(self.db_path)

        persisted = self.repository.load(self.slot)
        if persisted:
            self.state = persisted
            self.summary = self.state.pop("summary", None)
        else:
            self.state = {
                "world_state": "beginning",
                "inventory": [],
                "stats": {stat: 100 for stat in self.config["stats"]},
                "npc_rel": {},
                "log": [],
            }
            self.summary = None

        self.token_usage = 0

        self._bootstrap_hidden_lore()
        self.summarizer = LogSummarizer(
            self._instantiate_provider(summary_provider, "summarizer")
        )
        self._ensure_intro_narration()
        self.turn = self._infer_turn_counter()

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _instantiate_provider(self, provider: str, name: str) -> provider_base.BaseLLMProvider:
        provider_cls = provider_base.get_provider(provider)
        return provider_cls(self.config["models"][name]["create_params"])

    def _bootstrap_hidden_lore(self) -> None:
        if self.state.get("hidden_lore"):
            self.hidden_lore = self.state["hidden_lore"]
            return

        story_size = self.config["story_size"]
        npcs = self.config["npcs"]
        items = self.config["items"]
        prompt = (
            f"Expand the following seed into a rich hidden lore and story of ({story_size} words).\n"
            f"The story must focus on the protagonist (the user)'s journey.\n"
            f"The story should have a plot twist.\n"
            f"The story should include a maximum of {npcs} NPCs and {items} items.\n"
            f"The story must have a final boss, and the player must defeat it to win.\n"
            "Focus on mood, mystery, and stakes.\n"
            f"Seed: {self.hidden_lore}"
        )
        try:
            system_prompt = f"You craft hidden lore for a narrative game in the {self.config['language']} language."
            response = self.lore_generator.generate(
                system_prompt=system_prompt,
                user_prompt=prompt,
                context=None,
            )
            self.hidden_lore = response["text"].strip() or self.hidden_lore
        except Exception as e:
            print("Failed to generate hidden lore:", e)
            # Fall back to seed on failure
            pass
        self.state["hidden_lore"] = self.hidden_lore

    def process_turn(self, player_input: str) -> Dict[str, Any]:
        player_input = player_input.strip()
        if not player_input:
            raise ValueError("Player input cannot be empty")

        self.turn += 1

        system_prompt = prompts.build_system_prompt(self.config, self.hidden_lore)
        user_prompt = prompts.build_user_prompt(
            player_input=player_input,
            game_state={k: v for k, v in self.state.items() if k != "log"},
            log_history=self.state.get("log", []),
            summary=self.summary,
        )

        context = None
        try:
            narration = self.narrator.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context=context,
            )
        except Exception as exc:
            raise RuntimeError(f"Narrator failed: {exc}") from exc

        try:
            narrator_json = json.loads(narration["text"].strip())
            narrator_text = narrator_json["text"]
            self.state["stats"] = narrator_json["stats"]
            self.state["inventory"] = narrator_json["inventory"]
            self.state["npc_rel"] = narrator_json["npc_rel"]
            self.state["world_state"] = narrator_json["world_state"]
            if self.state["stats"].get("health", 100) < 1:
                self.state["world_state"] = "game_over"
            if self.state["stats"].get("sanity", 100) < 1:
                self.state["world_state"] = "game_over"
        except Exception as exc:
            raise RuntimeError(f"Failed to parse narrator response: {exc}") from exc
        usage = narration.get("usage", {})

        self.token_usage += usage.get("total_tokens", count_tokens([system_prompt, user_prompt, narrator_text]))

        log_entry = {
            "turn": self.turn,
            "player": player_input,
            "narrator": narrator_text,
        }
        self.state.setdefault("log", []).append(log_entry)

        # self._update_stats(player_input, narrator_text)
        self._maybe_summarize()
        self._persist()

        return {
            "narration": narrator_text,
            "state": self.state,
            "tokens": self.token_usage,
            "summary": self.summary,
        }

    def _maybe_summarize(self) -> None:
        log = self.state.get("log", [])
        if not log:
            return

        if not self.summarizer.should_summarize(
            total_tokens=self.token_usage, turn_count=len(log)
        ):
            return

        summary_text = self.summarizer.summarize(log)
        self.summary = summary_text
        # keep only last two log entries post-summary
        self.state["log"] = log[-2:]

    def _persist(self) -> None:
        self.repository.save(self.slot, game_state=self.state, summary=self.summary)

    def get_ui_state(self) -> Dict[str, Any]:
        return {
            "turn": self.turn,
            "stats": self.state.get("stats", {}),
            "inventory": self.state.get("inventory", []),
            "npc_rel": self.state.get("npc_rel", {}),
            "world_state": self.state.get("world_state", {}),
            "log": self.state.get("log", []),
            "summary": self.summary,
            "tokens": self.token_usage,
        }

    def _ensure_intro_narration(self) -> None:
        log = self.state.setdefault("log", [])
        if log:
            return

        system_prompt = prompts.build_system_prompt(self.config, self.hidden_lore)
        game_snapshot = {k: v for k, v in self.state.items() if k != "log"}
        user_prompt = prompts.build_intro_prompt(
            config=self.config,
            game_state=game_snapshot,
            hidden_lore=self.hidden_lore,
        )

        intro_text = "An uneasy hush hangs in the air."
        usage: Dict[str, Any] = {}
        try:
            narration = self.narrator.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context=None,
            )
            usage = narration.get("usage", {})
        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"Intro narration failed, falling back: {exc}")
        try:
            narrator_json = json.loads(narration["text"].strip())
            intro_text = narrator_json["text"]
            self.state["stats"] = narrator_json["stats"]
            self.state["inventory"] = narrator_json["inventory"]
            self.state["npc_rel"] = narrator_json["npc_rel"]
            self.state["world_state"] = narrator_json["world_state"]
            if self.state["stats"].get("health", 100) < 1:
                self.state["world_state"] = "game_over"
            if self.state["stats"].get("sanity", 100) < 1:
                self.state["world_state"] = "game_over"
        except Exception as exc:
            raise RuntimeError(f"Failed to parse narrator response: {exc}") from exc
        self.token_usage += usage.get(
            "total_tokens",
            count_tokens([system_prompt, user_prompt, intro_text]),
        )

        log.append(
            {
                "turn": 0,
                "player": "",
                "narrator": intro_text,
            }
        )
        self._persist()

    def _infer_turn_counter(self) -> int:
        log = self.state.get("log", [])
        if not log:
            return 0

        max_turn = 0
        for idx, entry in enumerate(log, start=1):
            if isinstance(entry, dict) and isinstance(entry.get("turn"), int):
                max_turn = max(max_turn, entry["turn"])
            else:
                max_turn = max(max_turn, idx)
        return max_turn
