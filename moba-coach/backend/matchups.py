"""Lane matchup tables and synergy matrix."""
from typing import Dict

try:
    from .champions import CHAMPIONS
except ImportError:
    from champions import CHAMPIONS


# 50 = even, >50 favours the first (row) champion.
# Only includes pairs that share at least one role.
LANE_MATCHUPS: Dict[str, Dict[str, int]] = {
    "reaver": {
        "ironclad": 58,
        "shade": 56,
        "warden": 60,
        "rapier": 55,
        "fang": 55,
        "sage": 57,
    },
    "rapier": {
        "ironclad": 58,
        "shade": 55,
        "reaver": 45,  
        "warden": 60,
        "fang": 56,
        "sage": 58,
    },
    "fang": {
        "shade": 58,
        "ironclad": 55,
        "warden": 62,
        "siren": 57,
    },
    "warden": {
        "fang": 40,
        "shade": 45,
        "siren": 43,
        "ironclad": 52,
    },
    "siren": {
        "whisper": 58,
        "solara": 56,
        "sage": 45,
    },
    "sage": {
        "siren": 55,
        "shade": 55,
        "whisper": 50,
        "solara": 50,
    },
    "ironclad": {
        "shade": 50,
        "warden": 52,
        "fang": 48,
        "rapier": 42,
        "reaver": 42,
    },
    "shade": {
        "ironclad": 50,
        "warden": 55,
        "fang": 42,
    },
    "whisper": {
        "solara": 50,
        "siren": 42,
        "sage": 50,
    },
    "solara": {
        "whisper": 50,
        "siren": 44,
        "sage": 50,
    },
}


SYNERGY_MATRIX: Dict[str, Dict[str, int]] = {
    "whisper": {"sage": 10, "ironclad": 8, "warden": 8, "solara": 6, "siren": 5, "shade": 5, "fang": 6, "reaver": 5, "rapier": 3},
    "sage": {"whisper": 10, "shade": 7, "siren": 7, "solara": 6, "ironclad": 7, "warden": 7, "fang": 6, "reaver": 6, "rapier": 4},
    "ironclad": {"solara": 9, "whisper": 8, "shade": 8, "siren": 7, "sage": 7, "fang": 6, "warden": 5, "reaver": 5, "rapier": 3},
    "warden": {"solara": 9, "whisper": 8, "sage": 7, "shade": 7, "siren": 7, "fang": 5, "ironclad": 5, "reaver": 5, "rapier": 3},
    "solara": {"ironclad": 9, "warden": 9, "sage": 6, "whisper": 6, "fang": 6, "shade": 6, "siren": 5, "reaver": 5, "rapier": 3},
    "fang": {"shade": 7, "siren": 7, "reaver": 7, "ironclad": 6, "sage": 6, "solara": 6, "whisper": 6, "warden": 5, "rapier": 4},
    "shade": {"fang": 7, "ironclad": 8, "sage": 7, "solara": 6, "whisper": 5, "siren": 6, "warden": 7, "reaver": 5, "rapier": 3},
    "siren": {"fang": 7, "ironclad": 7, "warden": 7, "sage": 7, "shade": 6, "solara": 5, "whisper": 5, "reaver": 5, "rapier": 3},
    "reaver": {"fang": 7, "sage": 6, "solara": 5, "whisper": 5, "ironclad": 5, "warden": 5, "shade": 5, "siren": 5, "rapier": 2},
    "rapier": {"sage": 5, "fang": 4, "solara": 3, "whisper": 3, "ironclad": 3, "warden": 3, "shade": 3, "siren": 3, "reaver": 2},
}


def get_matchup(champ_a: str, champ_b: str) -> int:
    """Return matchup value for champ_a vs champ_b. Defaults to 50."""
    return LANE_MATCHUPS.get(champ_a, {}).get(champ_b, 50)


def get_synergy(champ_a: str, champ_b: str) -> int:
    """Return synergy value for champ_a + champ_b. Defaults to 5."""
    if champ_a == champ_b:
        return 0
    return SYNERGY_MATRIX.get(champ_a, {}).get(champ_b, 5)


if __name__ == "__main__":
    # Sanity check: all keys are real champion ids
    for a, row in LANE_MATCHUPS.items():
        assert a in CHAMPIONS, a
        for b in row:
            assert b in CHAMPIONS, b
    for a, row in SYNERGY_MATRIX.items():
        assert a in CHAMPIONS, a
        for b in row:
            assert b in CHAMPIONS, b
    print("OK: matchups and synergies validated")
