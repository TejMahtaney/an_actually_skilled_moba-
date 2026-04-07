"""End-to-end match test: draft -> coaching -> simulate -> narrate."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from fastapi.testclient import TestClient
from main import app


def run():
    client = TestClient(app)

    client.post("/draft/start")
    client.post("/draft/ban", json={"champion_id": "rapier"})
    client.post("/draft/pick", json={"champion_id": "ironclad"})
    client.post("/draft/pick", json={"champion_id": "solara"})
    client.post("/draft/pick", json={"champion_id": "fang"})
    client.post("/draft/roles", json={"assignments": {
        "ironclad": "top", "solara": "bot", "fang": "jungle"
    }})
    state = client.get("/draft/state").json()
    print(f"Draft complete. Blue={state['blue_picks']} Red={state['red_picks']}")

    coaching = {
        "overall_strategy": "aggressive",
        "win_condition": "Snowball top with Fang ganks, then group for objectives.",
        "top_lane": {"approach": "aggressive", "priority": "kills",
                     "teamfight_role": "engage"},
        "bot_lane": {"approach": "standard", "priority": "cs",
                     "teamfight_role": "damage"},
        "jungle": {"pathing": "top_focus", "gank_frequency": "high",
                   "objective_focus": "medium"},
        "notes": "Don't fight late game — Solara needs items first.",
    }

    print("\n== /match/play ==")
    r = client.post("/match/play", json={"coaching": coaching}).json()
    print("Sim params:", r["sim_params"])
    print("Enemy params:", r["enemy_params"])
    mr = r["match_result"]
    print(f"\nWinner: {mr['winner']}  ({int(mr['duration_minutes'])} min)")
    print(f"Score:  {mr['blue_kills']} - {mr['red_kills']}")
    print(f"MVP:    {mr['mvp']}")
    print("\nNarration:")
    print(r["narration"])


if __name__ == "__main__":
    run()
