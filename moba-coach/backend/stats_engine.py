"""Compute final combat stats from champion base_stats + ability contributions."""
from typing import Dict

try:
    from .champions import CHAMPIONS
except ImportError:
    from champions import CHAMPIONS


_cache: Dict[str, dict] = {}
_contrib_cache: Dict[str, dict] = {}


def clear_cache() -> None:
    _cache.clear()
    _contrib_cache.clear()


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


_DAMAGE_WEIGHTS = {"active": 0.15, "passive": 0.05, "ultimate": 0.25}
_CC_WEIGHTS = {"active": 0.15, "passive": 0.1, "ultimate": 0.3}
_MOBILITY_BONUS = {"dash": 0.15, "blink": 0.2, "speed_boost": 0.1}
_DEFENSIVE_BONUS = {
    "shield": 0.1, "heal": 0.1, "damage_reduction": 0.15,
    "untargetable": 0.1, "parry": 0.1,
}


def compute_combat_stats(champion_id: str) -> dict:
    if champion_id in _cache:
        return _cache[champion_id]

    champ = CHAMPIONS[champion_id]
    stats = champ.base_stats.model_dump()

    for ab in champ.abilities:
        atype = ab.ability_type
        is_ult = atype == "ultimate"
        ult_mult = 1.5 if is_ult else 1.0

        # Damage contribution
        if ab.damage_amount > 0:
            w = _DAMAGE_WEIGHTS.get(atype, 0.15)
            if ab.damage_type == "physical":
                stats["attack_damage"] += ab.damage_amount * w
            elif ab.damage_type == "magic":
                stats["magic_damage"] += ab.damage_amount * w

        # CC contribution
        if ab.cc_duration > 0:
            w = _CC_WEIGHTS.get(atype, 0.15)
            stats["cc"] += ab.cc_duration * w

        # Mobility
        if ab.mobility_grant != "none":
            stats["mobility"] += _MOBILITY_BONUS.get(ab.mobility_grant, 0.0) * ult_mult

        # Defensive
        if ab.defensive_property != "none":
            stats["durability"] += _DEFENSIVE_BONUS.get(ab.defensive_property, 0.0) * ult_mult

        # Tag-based
        if "waveclear" in ab.tags:
            stats["waveclear"] += 0.15 if is_ult else 0.1
        if any(t in ab.tags for t in ("peel", "utility")):
            stats["utility"] += 0.15 if is_ult else 0.1

    # Burst — high/medium cooldown abilities
    burst_bonus = 0.0
    sustain_bonus = 0.0
    for ab in champ.abilities:
        if ab.damage_amount <= 0:
            continue
        if ab.cooldown in ("high", "medium"):
            w = 0.3 if ab.ability_type == "ultimate" else 0.15
            burst_bonus += ab.damage_amount * w
        if ab.cooldown == "low":
            w = 0.2 if ab.ability_type == "ultimate" else 0.15
            sustain_bonus += ab.damage_amount * w
    stats["burst"] += burst_bonus
    stats["sustain_damage"] += sustain_bonus

    for k in stats:
        stats[k] = _clamp01(stats[k])

    _cache[champion_id] = stats
    return stats


def compute_team_contribution(champion_id: str) -> dict:
    if champion_id in _contrib_cache:
        return _contrib_cache[champion_id]

    champ = CHAMPIONS[champion_id]
    tc = champ.team_contribution.model_dump()

    for ab in champ.abilities:
        is_ult = ab.ability_type == "ultimate"
        if "engage" in ab.tags:
            tc["engage"] += 0.2 if is_ult else 0.1
        if "peel" in ab.tags:
            tc["peel"] += 0.15 if is_ult else 0.1
        if "frontline" in ab.tags:
            tc["frontline"] += 0.1
        if ab.range == "long" and ab.damage_amount > 0.4:
            tc["backline_threat"] += 0.1

    for k in tc:
        tc[k] = _clamp01(tc[k])

    _contrib_cache[champion_id] = tc
    return tc


if __name__ == "__main__":
    print(f"{'champion':<12} {'stat':<18} {'base':>6} {'computed':>10}  delta")
    print("-" * 60)
    for cid, champ in CHAMPIONS.items():
        base = champ.base_stats.model_dump()
        final = compute_combat_stats(cid)
        print(f"\n== {champ.icon} {champ.name} ({champ.tag}) ==")
        for k in base:
            b = base[k]
            f = final[k]
            marker = "  ←" if abs(f - b) > 0.001 else ""
            print(f"{'':<12} {k:<18} {b:>6.2f} {f:>10.2f}{marker}")
        tc = compute_team_contribution(cid)
        print(f"  team_contrib: {tc}")
