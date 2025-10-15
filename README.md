## LLM-Based Adventure Game

Run a modular, genre-flexible text adventure locally with either OpenAI's GPT models or a local Ollama runtime. Each session keeps track of stats, inventory, relationships, and a hidden lore thread while maintaining continuity through on-demand summarisation.

### Features

- **Configurable genres** using YAML seeds for lore, tone, and model selection.
- **SQLite persistence** for save slots, summaries, and hidden lore.
- **Pluggable LLM providers** with swappable narrators (`openai` or `ollama`).
- **Token-aware context management** with automatic history summarisation.
- **Flask UI** for interactive play with stats, inventory, and log panels.

### Getting Started

```bash
uv sync
python -m adventure_game.app
```

By default the game uses the provider defined in `configs/config.yaml`. Override it via `ADVENTURE_PROVIDER`:

```bash
export ADVENTURE_PROVIDER="ollama/llama3"
```

For OpenAI you must also specify `OPENAI_API_KEY`.

### Customising the Adventure

- Adjust `configs/config.yaml` to change genre, stats, and model choices.
- Hidden lore is expanded on start-up using `models.lore_generator`.
- Gameplay state is persisted in `adventure_game/game_state.db`.

### Safety Rules

The narrator enforces anti-leak directives to avoid exposing hidden lore or meta notes, responding with in-world ambiguity when challenged.

### Project Structure

The repo matches the scaffold provided in the original request, with modules split across `core`, `models`, `templates`, `static`, and utility helpers for token tracking.
