"""End-to-end draft API test using FastAPI's TestClient."""
from fastapi.testclient import TestClient

try:
    from .main import app
except ImportError:
    from main import app


def run():
    client = TestClient(app)

    print("== POST /draft/start ==")
    r = client.post("/draft/start")
    print(r.json())

    print("\n== POST /draft/ban (rapier) ==")
    r = client.post("/draft/ban", json={"champion_id": "rapier"})
    print(r.json())

    print("\n== POST /draft/pick (ironclad) ==")
    r = client.post("/draft/pick", json={"champion_id": "ironclad"})
    print(r.json())

    state = client.get("/draft/state").json()
    print(f"\nstate after enemy 2-pick: step={state['step']} blue={state['blue_picks']} red={state['red_picks']}")

    # Pick two more for player
    avail = state["available"]
    bot = next(c for c in avail if "bot" in __import__("champions").CHAMPIONS[c].roles)
    print(f"\n== POST /draft/pick ({bot}) ==")
    r = client.post("/draft/pick", json={"champion_id": bot})
    state = r.json()
    print(f"step={state['step']} blue={state['blue_picks']}")

    avail = state["available"]
    from champions import CHAMPIONS
    jungle = next(c for c in avail if "jungle" in CHAMPIONS[c].roles)
    print(f"\n== POST /draft/pick ({jungle}) ==")
    r = client.post("/draft/pick", json={"champion_id": jungle})
    state = r.json()
    print(state)

    # Build role assignments
    blue = state["blue_picks"]
    assignments = {}
    remaining = {"top", "bot", "jungle"}
    for cid in blue:
        for role in CHAMPIONS[cid].roles:
            if role in remaining:
                assignments[cid] = role
                remaining.discard(role)
                break

    print(f"\n== POST /draft/roles {assignments} ==")
    r = client.post("/draft/roles", json={"assignments": assignments})
    print(r.json())


if __name__ == "__main__":
    run()
