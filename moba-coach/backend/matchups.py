"""Dynamic matchup and synergy computation from computed combat stats."""
from typing import Dict

try:
    from .champions import CHAMPIONS
    from .stats_engine import compute_combat_stats, compute_team_contribution
except ImportError:
    from champions import CHAMPIONS
    from stats_engine import compute_combat_stats, compute_team_contribution


# ---------------------------------------------------------------------------
# Interaction weights — how much each stat advantage shifts a matchup.
# ---------------------------------------------------------------------------
W_BURST_VS_LOW_DURABILITY = 6.0    # burst attackers punish squishies
W_SUSTAIN_VS_BURST = 4.0           # sustained damage outlasts burst windows
W_RANGE_VS_LOW_MOBILITY = 5.0      # ranged champions kite immobile ones
W_MOBILITY_VS_CC = 4.0             # mobile champions dodge skillshot CC
W_CC_VS_LOW_MOBILITY = 5.0         # CC locks down immobile targets
W_DURABILITY_VS_LOW_SUSTAIN = 3.0  # tanks stonewall low-DPS champions
W_WAVECLEAR_ADVANTAGE = 2.0        # lane pressure from better waveclear
W_DAMAGE_TYPE_MISMATCH = 2.0       # mixed damage is harder to itemise against


def _directional_delta(a: dict, b: dict) -> float:
    """Return how much `a` beats `b` on the matchup axis."""
    delta = 0.0

    # Burst vs low durability
    if a["burst"] > 0.5 and b["durability"] < 0.5:
        delta += (a["burst"] - b["durability"]) * W_BURST_VS_LOW_DURABILITY

    # Sustain damage vs bursty, squishy target
    if a["sustain_damage"] > 0.6 and b["burst"] > 0.5 and b["durability"] < 0.5:
        delta += (a["sustain_damage"] - b["durability"]) * W_SUSTAIN_VS_BURST

    # Range vs low mobility
    if a["range"] > 0.6 and b["mobility"] < 0.4:
        delta += (a["range"] - b["mobility"]) * W_RANGE_VS_LOW_MOBILITY

    # Mobility evades CC
    if a["mobility"] > 0.6 and b["cc"] > 0.4:
        delta += (a["mobility"] - b["cc"]) * W_MOBILITY_VS_CC

    # CC locks down low-mobility opponents
    if a["cc"] > 0.5 and b["mobility"] < 0.4:
        delta += (a["cc"] - b["mobility"]) * W_CC_VS_LOW_MOBILITY

    # Durability walls low-damage opponents
    a_dmg = max(a["attack_damage"], a["magic_damage"])
    b_dmg = max(b["attack_damage"], b["magic_damage"])
    if a["durability"] > 0.7 and b["sustain_damage"] < 0.4 and b_dmg < 0.5:
        delta += (a["durability"] - b["sustain_damage"]) * W_DURABILITY_VS_LOW_SUSTAIN

    # Waveclear advantage
    if a["waveclear"] - b["waveclear"] > 0.2:
        delta += (a["waveclear"] - b["waveclear"]) * W_WAVECLEAR_ADVANTAGE

    # Mixed damage is harder to itemise against
    a_mixed = min(a["attack_damage"], a["magic_damage"]) > 0.25
    if a_mixed and a_dmg > 0.5:
        delta += W_DAMAGE_TYPE_MISMATCH * 0.5

    return delta


def get_matchup(champ_a: str, champ_b: str) -> int:
    if champ_a == champ_b:
        return 50
    a = compute_combat_stats(champ_a)
    b = compute_combat_stats(champ_b)
    score = 50.0 + _directional_delta(a, b) - _directional_delta(b, a)
    return int(round(max(30, min(70, score))))


def get_synergy(champ_a: str, champ_b: str) -> int:
    if champ_a == champ_b:
        return 0

    a = compute_combat_stats(champ_a)
    b = compute_combat_stats(champ_b)
    ta = compute_team_contribution(champ_a)
    tb = compute_team_contribution(champ_b)

    score = 5.0

    # Frontline + backline_threat
    if (ta["frontline"] > 0.6 and tb["backline_threat"] > 0.6) or \
       (tb["frontline"] > 0.6 and ta["backline_threat"] > 0.6):
        score += 2.0

    # Engage + burst follow-up
    if (ta["engage"] > 0.6 and b["burst"] > 0.6) or \
       (tb["engage"] > 0.6 and a["burst"] > 0.6):
        score += 1.5

    # CC setup + sustain damage
    if (a["cc"] > 0.5 and b["sustain_damage"] > 0.6) or \
       (b["cc"] > 0.5 and a["sustain_damage"] > 0.6):
        score += 1.0

    # Peel protecting squishy carry
    if (ta["peel"] > 0.6 and b["durability"] < 0.3) or \
       (tb["peel"] > 0.6 and a["durability"] < 0.3):
        score += 1.5

    # Utility enchanter + high-damage carry
    a_dmg = max(a["attack_damage"], a["magic_damage"])
    b_dmg = max(b["attack_damage"], b["magic_damage"])
    if (a["utility"] > 0.6 and b_dmg > 0.6) or \
       (b["utility"] > 0.6 and a_dmg > 0.6):
        score += 1.0

    # Redundancy penalties
    champ_a_obj = CHAMPIONS[champ_a]
    champ_b_obj = CHAMPIONS[champ_b]
    if champ_a_obj.tag == champ_b_obj.tag:
        score -= 1.0

    if ta["frontline"] < 0.3 and tb["frontline"] < 0.3 and \
       ta["peel"] < 0.3 and tb["peel"] < 0.3:
        score -= 2.0

    if a["range"] < 0.3 and b["range"] < 0.3 and \
       ta["engage"] < 0.3 and tb["engage"] < 0.3:
        score -= 1.0

    return int(round(max(0, min(10, score))))


if __name__ == "__main__":
    ids = list(CHAMPIONS.keys())

    print("=== MATCHUP GRID (row vs col, 50=even) ===")
    header = "         " + " ".join(f"{c[:4]:>5}" for c in ids)
    print(header)
    for a in ids:
        row = f"{a[:8]:<8} " + " ".join(f"{get_matchup(a, b):>5}" for b in ids)
        print(row)

    print("\n=== SYNERGY GRID (0-10) ===")
    print(header)
    for a in ids:
        row = f"{a[:8]:<8} " + " ".join(f"{get_synergy(a, b):>5}" for b in ids)
        print(row)

    # Validation
    for a in ids:
        for b in ids:
            m = get_matchup(a, b)
            assert 30 <= m <= 70, f"{a} vs {b} = {m}"
            if a != b:
                # Symmetry: a vs b and b vs a should sum to ~100
                rev = get_matchup(b, a)
                assert abs(m + rev - 100) <= 2, \
                    f"asymmetric: {a}vs{b}={m}, {b}vs{a}={rev}"
            s = get_synergy(a, b)
            assert 0 <= s <= 10, f"synergy {a}+{b} = {s}"
            if a != b:
                assert get_synergy(a, b) == get_synergy(b, a), \
                    f"synergy not symmetric: {a}+{b}"
    print("\nOK: matchups and synergies validated")
