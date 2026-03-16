default persistent._mas_xiangqi_seen_rules = False
default persistent._mas_xiangqi_stats = {
    "wins": 0,
    "losses": 0,
    "draws": 0
}
default persistent._mas_xiangqi_difficulty = "normal"

init -990 python:
    store.mas_submod_utils.Submod(
        author="Codex",
        name="MAS Chinese Chess",
        description="Adds a playable Chinese chess minigame to the Play menu.",
        version="0.1.0"
    )

init 5 python:
    addEvent(
        Event(
            persistent._mas_game_database,
            eventlabel="mas_xiangqi_start",
            prompt="中国象棋",
            unlocked=True
        ),
        code="GME",
        restartBlacklist=True
    )
