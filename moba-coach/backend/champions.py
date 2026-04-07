"""Champion definitions for the 3v3 MOBA."""
from typing import Dict, List

try:
    from .models import Champion
except ImportError:
    from models import Champion


CHAMPIONS: Dict[str, Champion] = {
    "ironclad": Champion(
        id="ironclad",
        name="Ironclad",
        tag="Tank",
        icon="🛡️",
        roles=["top", "jungle"],
        power_curve={"early": 0.4, "mid": 0.7, "late": 0.6},
        description="Tanky engager with AoE knockup ult.",
    ),
    "shade": Champion(
        id="shade",
        name="Shade",
        tag="Assassin",
        icon="🗡️",
        roles=["top", "jungle"],
        power_curve={"early": 0.5, "mid": 0.8, "late": 0.5},
        description="Burst physical assassin.",
    ),
    "solara": Champion(
        id="solara",
        name="Solara",
        tag="Mage",
        icon="☀️",
        roles=["bot"],
        power_curve={"early": 0.3, "mid": 0.6, "late": 0.9},
        description="Control mage with zone denial and AoE pull ult.",
    ),
    "reaver": Champion(
        id="reaver",
        name="Reaver",
        tag="Juggernaut",
        icon="🪓",
        roles=["top"],
        power_curve={"early": 0.8, "mid": 0.7, "late": 0.4},
        description="Lane bully with bleed stacks and execute ult.",
    ),
    "whisper": Champion(
        id="whisper",
        name="Whisper",
        tag="Marksman",
        icon="🎯",
        roles=["bot"],
        power_curve={"early": 0.3, "mid": 0.5, "late": 0.95},
        description="Long-range carry, strongest late game DPS.",
    ),
    "sage": Champion(
        id="sage",
        name="Sage",
        tag="Enchanter",
        icon="✨",
        roles=["bot", "top"],
        power_curve={"early": 0.5, "mid": 0.8, "late": 0.7},
        description="Shields and buffs allies, anti-dive ult.",
    ),
    "fang": Champion(
        id="fang",
        name="Fang",
        tag="Fighter",
        icon="👊",
        roles=["jungle", "top"],
        power_curve={"early": 0.9, "mid": 0.6, "late": 0.3},
        description="Mobile early-game jungler, high gank pressure.",
    ),
    "siren": Champion(
        id="siren",
        name="Siren",
        tag="Mage Assassin",
        icon="💫",
        roles=["bot", "jungle"],
        power_curve={"early": 0.5, "mid": 0.8, "late": 0.6},
        description="Charm skillshot into burst, triple dash ult.",
    ),
    "warden": Champion(
        id="warden",
        name="Warden",
        tag="Tank",
        icon="⛓️",
        roles=["jungle", "top"],
        power_curve={"early": 0.3, "mid": 0.6, "late": 0.85},
        description="AoE root ult, best teamfight CC.",
    ),
    "rapier": Champion(
        id="rapier",
        name="Rapier",
        tag="Duelist",
        icon="⚔️",
        roles=["top"],
        power_curve={"early": 0.4, "mid": 0.6, "late": 0.95},
        description="Unbeatable 1v1 late game, parry ability, split-push threat.",
    ),
}


def get_champion(champion_id: str) -> Champion:
    return CHAMPIONS[champion_id]


def champions_by_role(role: str) -> List[Champion]:
    return [c for c in CHAMPIONS.values() if role in c.roles]


if __name__ == "__main__":
    assert len(CHAMPIONS) == 10, f"Expected 10 champions, got {len(CHAMPIONS)}"
    for cid, champ in CHAMPIONS.items():
        assert cid == champ.id
        assert champ.roles, f"{cid} has no roles"
        for phase in ("early", "mid", "late"):
            assert 0.0 <= champ.power_curve[phase] <= 1.0
    print(f"OK: loaded {len(CHAMPIONS)} champions")
    for c in CHAMPIONS.values():
        print(f"  {c.icon} {c.name} ({c.tag}) - {'/'.join(c.roles)}")
