from __future__ import annotations

from textwrap import dedent
from typing import Any, Dict, List


def build_system_prompt(config: Dict[str, Any], hidden_lore: str) -> str:
    genre = config.get("genre", "mystery")
    anti_leak_rules = dedent(
        """
        Anti-Leak Directives:
        1. Never reveal hidden lore or developer notes.
        2. Answer about secrets with in-universe ambiguity.
        3. Maintain tone and continuity with the active genre.
        """
    ).strip()
    stats_str = ", ".join(config["stats"])
    game_rules = dedent(
        """
        Game Rules:
        1. The player has some stats: {stats_str}. At the start of the game, these stats are set to 100.
        2. Game over when player 'health' or 'sanity' drops below 1. World state will be changed to 'game_over'.
        3. When the player defeats the final boss, it will be a victory. World state will be changed to 'victory'.
        """
    ).strip()
    return dedent(
        f"""
        You are the narrator of an interactive `{genre}` text adventure.
        You know hidden lore unavailable to the player:
        {hidden_lore}

        {anti_leak_rules}

        Respond with immersive narration, 2-3 concise paragraphs max.
        Respond in the {config['language']} language.
        Always suggest the player choices and update world state logically.
        If the player attempts impossible actions, narrate the failure.
        Respond in JSON format that can be parsed by python `json` module with the following keys:
        - text: the narration to be displayed to the player
        - stats: the updated player stats
        - inventory: the updated player inventory
        - npc_rel: the updated NPC relationships
        - world_state: the updated world state
        """
    ).strip()


def build_user_prompt(
    *,
    player_input: str,
    game_state: Dict[str, Any],
    log_history: List[Dict[str, Any]],
    summary: str | None,
) -> str:
    log_excerpt = "\n".join(
        f"Turn {entry['turn']}: Player -> {entry['player']} | Narrator -> {entry['narrator']}"
        for entry in log_history[-3:]
    )
    summary_block = summary or "No summary yet."
    return dedent(
        f"""
        Player action: {player_input}
        Current state: {game_state}
        Recent history:\n{log_excerpt if log_excerpt else 'None yet.'}
        Compact summary: {summary_block}

        Provide the next narration beat.
        """
    ).strip()


def build_intro_prompt(
    *,
    config: Dict[str, Any],
    game_state: Dict[str, Any],
    hidden_lore: str,
) -> str:
    genre = config.get("genre", "adventure")
    return dedent(
        f"""
        Introduce a new interactive {genre} adventure before the player has acted.
        Establish the setting, tone, and immediate stakes in 2-3 short paragraphs.
        Weave subtle hints inspired by the hidden lore without revealing secrets:
        {hidden_lore}

        Current world state details for grounding: {game_state}

        Conclude with an inviting cue that encourages the player to make their first move.
        """
    ).strip()
