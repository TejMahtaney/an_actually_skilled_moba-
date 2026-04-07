"""Champion definitions for the 3v3 MOBA."""
from typing import Dict, List

try:
    from .models import AbilityProperties, Champion, CombatStats, TeamContribution
except ImportError:
    from models import AbilityProperties, Champion, CombatStats, TeamContribution


def _ab(**kwargs) -> AbilityProperties:
    defaults = {
        "damage_type": "none",
        "damage_amount": 0.0,
        "cc_type": "none",
        "cc_duration": 0.0,
        "mobility_grant": "none",
        "defensive_property": "none",
        "tags": [],
        "description": "",
    }
    defaults.update(kwargs)
    return AbilityProperties(**defaults)


CHAMPIONS: Dict[str, Champion] = {
    "ironclad": Champion(
        id="ironclad",
        name="Ironclad",
        tag="Tank",
        icon="🛡️",
        roles=["top", "jungle"],
        power_curve={"early": 0.4, "mid": 0.7, "late": 0.6},
        abilities=[
            _ab(name="Shield Bash", ability_type="active", damage_type="physical",
                damage_amount=0.3, cc_type="stun", cc_duration=0.4,
                targeting="skillshot", range="melee", cooldown="medium",
                tags=["engage", "peel"],
                description="Slams shield forward, stunning the first target hit."),
            _ab(name="Bulwark", ability_type="active", targeting="self",
                range="melee", defensive_property="damage_reduction",
                cooldown="medium", tags=["frontline"],
                description="Braces for impact, massively reducing incoming damage."),
            _ab(name="Tectonic Slam", ability_type="ultimate", damage_type="physical",
                damage_amount=0.5, cc_type="knockup", cc_duration=0.7,
                targeting="aoe", range="short", cooldown="high",
                tags=["engage", "teamfight", "aoe"],
                description="Crushes the ground, launching all nearby enemies skyward."),
        ],
        base_stats=CombatStats(
            attack_damage=0.3, magic_damage=0.1, durability=0.85, mobility=0.2,
            cc=0.5, range=0.2, burst=0.2, sustain_damage=0.25, waveclear=0.4,
            utility=0.3),
        team_contribution=TeamContribution(
            engage=0.85, peel=0.5, frontline=0.9, backline_threat=0.05),
    ),
    "shade": Champion(
        id="shade",
        name="Shade",
        tag="Assassin",
        icon="🗡️",
        roles=["top", "jungle"],
        power_curve={"early": 0.5, "mid": 0.8, "late": 0.5},
        abilities=[
            _ab(name="Shadow Strike", ability_type="active", damage_type="physical",
                damage_amount=0.7, cc_type="slow", cc_duration=0.2,
                targeting="single_target", range="melee", mobility_grant="dash",
                cooldown="low", tags=["burst", "gap_closer"],
                description="Dashes to a target and strikes for heavy damage."),
            _ab(name="Vanish", ability_type="active", targeting="self",
                range="melee", mobility_grant="speed_boost",
                defensive_property="untargetable", cooldown="medium",
                tags=["escape", "stealth"],
                description="Melts into shadow, briefly untargetable and hastened."),
            _ab(name="Death Mark", ability_type="ultimate", damage_type="physical",
                damage_amount=0.9, targeting="single_target", range="melee",
                cooldown="high", tags=["execute", "burst", "assassination"],
                description="Marks a target for death, delivering a killing blow."),
        ],
        base_stats=CombatStats(
            attack_damage=0.8, magic_damage=0.1, durability=0.25, mobility=0.85,
            cc=0.15, range=0.15, burst=0.9, sustain_damage=0.3, waveclear=0.3,
            utility=0.05),
        team_contribution=TeamContribution(
            engage=0.3, peel=0.05, frontline=0.1, backline_threat=0.4),
    ),
    "solara": Champion(
        id="solara",
        name="Solara",
        tag="Mage",
        icon="☀️",
        roles=["bot"],
        power_curve={"early": 0.3, "mid": 0.6, "late": 0.9},
        abilities=[
            _ab(name="Solar Flare", ability_type="active", damage_type="magic",
                damage_amount=0.6, cc_type="slow", cc_duration=0.3,
                targeting="aoe", range="long", cooldown="medium",
                tags=["poke", "waveclear", "zone"],
                description="Calls down a burst of sunlight that scorches an area."),
            _ab(name="Radiant Field", ability_type="active", damage_type="magic",
                damage_amount=0.3, cc_type="silence", cc_duration=0.4,
                targeting="aoe", range="medium", cooldown="medium",
                tags=["zone", "peel"],
                description="Creates a field of light that silences enemies inside."),
            _ab(name="Gravity Well", ability_type="ultimate", damage_type="magic",
                damage_amount=0.7, cc_type="pull", cc_duration=0.8,
                targeting="aoe", range="long", cooldown="high",
                tags=["teamfight", "engage", "aoe", "zone"],
                description="Collapses a star, pulling all enemies to its centre."),
        ],
        base_stats=CombatStats(
            attack_damage=0.05, magic_damage=0.8, durability=0.25, mobility=0.2,
            cc=0.55, range=0.85, burst=0.5, sustain_damage=0.6, waveclear=0.8,
            utility=0.3),
        team_contribution=TeamContribution(
            engage=0.5, peel=0.6, frontline=0.05, backline_threat=0.75),
    ),
    "reaver": Champion(
        id="reaver",
        name="Reaver",
        tag="Juggernaut",
        icon="🪓",
        roles=["top"],
        power_curve={"early": 0.8, "mid": 0.7, "late": 0.4},
        abilities=[
            _ab(name="Rending Cleave", ability_type="active", damage_type="physical",
                damage_amount=0.65, targeting="aoe", range="melee", cooldown="low",
                tags=["waveclear", "sustain_damage"],
                description="Sweeps a massive axe in a wide arc, bleeding all it hits."),
            _ab(name="Blood Frenzy", ability_type="active", targeting="self",
                range="melee", defensive_property="heal", cooldown="medium",
                tags=["sustain", "frontline"],
                description="Drinks deep from fresh wounds, restoring health."),
            _ab(name="Guillotine", ability_type="ultimate", damage_type="physical",
                damage_amount=0.85, targeting="single_target", range="melee",
                cooldown="high", tags=["execute", "burst"],
                description="Brings the axe down on a wounded foe for lethal damage."),
        ],
        base_stats=CombatStats(
            attack_damage=0.8, magic_damage=0.05, durability=0.7, mobility=0.2,
            cc=0.15, range=0.15, burst=0.5, sustain_damage=0.75, waveclear=0.6,
            utility=0.05),
        team_contribution=TeamContribution(
            engage=0.3, peel=0.1, frontline=0.7, backline_threat=0.1),
    ),
    "whisper": Champion(
        id="whisper",
        name="Whisper",
        tag="Marksman",
        icon="🎯",
        roles=["bot"],
        power_curve={"early": 0.3, "mid": 0.5, "late": 0.95},
        abilities=[
            _ab(name="Piercing Shot", ability_type="active", damage_type="physical",
                damage_amount=0.5, targeting="skillshot", range="long",
                cooldown="low", tags=["poke", "sustain_damage"],
                description="Fires an arrow that pierces through everything in its path."),
            _ab(name="Tumble", ability_type="active", targeting="self",
                range="short", mobility_grant="dash", cooldown="low",
                tags=["escape", "reposition"],
                description="Rolls a short distance, resetting attack rhythm."),
            _ab(name="Barrage", ability_type="ultimate", damage_type="physical",
                damage_amount=0.8, targeting="aoe", range="long", cooldown="high",
                tags=["teamfight", "sustain_damage", "aoe"],
                description="Unleashes a storm of arrows across a wide area."),
        ],
        base_stats=CombatStats(
            attack_damage=0.75, magic_damage=0.05, durability=0.15, mobility=0.4,
            cc=0.05, range=0.95, burst=0.3, sustain_damage=0.9, waveclear=0.5,
            utility=0.05),
        team_contribution=TeamContribution(
            engage=0.05, peel=0.05, frontline=0.05, backline_threat=0.95),
    ),
    "sage": Champion(
        id="sage",
        name="Sage",
        tag="Enchanter",
        icon="✨",
        roles=["bot", "top"],
        power_curve={"early": 0.5, "mid": 0.8, "late": 0.7},
        abilities=[
            _ab(name="Blessing", ability_type="active", targeting="ally",
                range="medium", defensive_property="shield", cooldown="low",
                tags=["peel", "utility"],
                description="Wraps an ally in radiant light, granting a shield."),
            _ab(name="Starlight", ability_type="active", damage_type="magic",
                damage_amount=0.2, cc_type="slow", cc_duration=0.3,
                targeting="skillshot", range="long", cooldown="medium",
                tags=["poke", "peel"],
                description="Hurls a mote of starlight that chills its target."),
            _ab(name="Divine Barrier", ability_type="ultimate", targeting="aoe",
                range="medium", defensive_property="shield", cooldown="high",
                tags=["teamfight", "peel", "anti_dive"],
                description="Consecrates the ground, shielding all allies within."),
        ],
        base_stats=CombatStats(
            attack_damage=0.1, magic_damage=0.25, durability=0.35, mobility=0.3,
            cc=0.3, range=0.7, burst=0.1, sustain_damage=0.15, waveclear=0.25,
            utility=0.9),
        team_contribution=TeamContribution(
            engage=0.05, peel=0.9, frontline=0.15, backline_threat=0.1),
    ),
    "fang": Champion(
        id="fang",
        name="Fang",
        tag="Fighter",
        icon="👊",
        roles=["jungle", "top"],
        power_curve={"early": 0.9, "mid": 0.6, "late": 0.3},
        abilities=[
            _ab(name="Lunge", ability_type="active", damage_type="physical",
                damage_amount=0.55, cc_type="slow", cc_duration=0.25,
                targeting="single_target", range="short", mobility_grant="dash",
                cooldown="low", tags=["gap_closer", "gank"],
                description="Pounces on a target, slowing and mauling them."),
            _ab(name="Feral Instinct", ability_type="passive", targeting="self",
                range="melee", mobility_grant="speed_boost", cooldown="low",
                tags=["hunt", "vision"],
                description="Senses wounded prey, gaining speed toward them."),
            _ab(name="Primal Fury", ability_type="ultimate", damage_type="physical",
                damage_amount=0.7, cc_type="stun", cc_duration=0.5,
                targeting="single_target", range="short", mobility_grant="dash",
                cooldown="high", tags=["gank", "assassination", "engage"],
                description="Unleashes a savage combo that stuns and shreds a target."),
        ],
        base_stats=CombatStats(
            attack_damage=0.7, magic_damage=0.05, durability=0.35, mobility=0.9,
            cc=0.3, range=0.2, burst=0.65, sustain_damage=0.4, waveclear=0.4,
            utility=0.1),
        team_contribution=TeamContribution(
            engage=0.6, peel=0.1, frontline=0.3, backline_threat=0.3),
    ),
    "siren": Champion(
        id="siren",
        name="Siren",
        tag="Mage Assassin",
        icon="💫",
        roles=["bot", "jungle"],
        power_curve={"early": 0.5, "mid": 0.8, "late": 0.6},
        abilities=[
            _ab(name="Allure", ability_type="active", damage_type="magic",
                damage_amount=0.3, cc_type="charm", cc_duration=0.6,
                targeting="skillshot", range="medium", cooldown="medium",
                tags=["engage", "pick", "peel"],
                description="Sends out an enchanting kiss that charms the first target hit."),
            _ab(name="Arcane Bolt", ability_type="active", damage_type="magic",
                damage_amount=0.6, targeting="single_target", range="medium",
                cooldown="low", tags=["burst", "poke"],
                description="Hurls a bolt of raw arcane force."),
            _ab(name="Spirit Rush", ability_type="ultimate", damage_type="magic",
                damage_amount=0.65, targeting="single_target", range="medium",
                mobility_grant="dash", cooldown="medium",
                tags=["burst", "assassination", "reposition"],
                description="Blinks through targets three times, leaving searing trails."),
        ],
        base_stats=CombatStats(
            attack_damage=0.1, magic_damage=0.8, durability=0.2, mobility=0.75,
            cc=0.4, range=0.6, burst=0.8, sustain_damage=0.35, waveclear=0.35,
            utility=0.15),
        team_contribution=TeamContribution(
            engage=0.4, peel=0.3, frontline=0.05, backline_threat=0.7),
    ),
    "warden": Champion(
        id="warden",
        name="Warden",
        tag="Tank",
        icon="⛓️",
        roles=["jungle", "top"],
        power_curve={"early": 0.3, "mid": 0.6, "late": 0.85},
        abilities=[
            _ab(name="Chain Lash", ability_type="active", damage_type="magic",
                damage_amount=0.25, cc_type="root", cc_duration=0.5,
                targeting="skillshot", range="medium", cooldown="medium",
                tags=["peel", "engage"],
                description="Whips a chain forward, rooting the first target hit."),
            _ab(name="Stone Skin", ability_type="passive", targeting="self",
                range="melee", defensive_property="damage_reduction",
                cooldown="low", tags=["frontline"],
                description="Hardens skin to stone, absorbing a portion of all damage."),
            _ab(name="Earthen Prison", ability_type="ultimate", damage_type="magic",
                damage_amount=0.4, cc_type="root", cc_duration=0.9,
                targeting="aoe", range="medium", cooldown="high",
                tags=["teamfight", "engage", "aoe", "peel"],
                description="Erupts stone pillars that trap all enemies in an area."),
        ],
        base_stats=CombatStats(
            attack_damage=0.15, magic_damage=0.3, durability=0.9, mobility=0.15,
            cc=0.7, range=0.4, burst=0.15, sustain_damage=0.2, waveclear=0.35,
            utility=0.4),
        team_contribution=TeamContribution(
            engage=0.8, peel=0.75, frontline=0.95, backline_threat=0.05),
    ),
    "rapier": Champion(
        id="rapier",
        name="Rapier",
        tag="Duelist",
        icon="⚔️",
        roles=["top"],
        power_curve={"early": 0.4, "mid": 0.6, "late": 0.95},
        abilities=[
            _ab(name="Lunge Strike", ability_type="active", damage_type="physical",
                damage_amount=0.55, targeting="single_target", range="melee",
                mobility_grant="dash", cooldown="low",
                tags=["sustain_damage", "gap_closer", "split_push"],
                description="Darts forward with a precise thrust."),
            _ab(name="Riposte", ability_type="active", cc_type="stun",
                cc_duration=0.3, targeting="self", range="melee",
                defensive_property="parry", cooldown="medium",
                tags=["outplay", "peel"],
                description="Parries the next incoming attack and stuns the attacker."),
            _ab(name="Grand Challenge", ability_type="ultimate", damage_type="physical",
                damage_amount=0.8, targeting="single_target", range="melee",
                cooldown="high", tags=["duel", "execute", "split_push"],
                description="Challenges a single foe to a duel to the death."),
        ],
        base_stats=CombatStats(
            attack_damage=0.75, magic_damage=0.05, durability=0.4, mobility=0.55,
            cc=0.15, range=0.15, burst=0.4, sustain_damage=0.85, waveclear=0.45,
            utility=0.05),
        team_contribution=TeamContribution(
            engage=0.1, peel=0.15, frontline=0.25, backline_threat=0.2),
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
        assert len(champ.abilities) == 3, \
            f"{cid} has {len(champ.abilities)} abilities, expected 3"
        ults = [a for a in champ.abilities if a.ability_type == "ultimate"]
        assert len(ults) == 1, \
            f"{cid} has {len(ults)} ultimates, expected exactly 1"
    print(f"OK: loaded {len(CHAMPIONS)} champions")
    for c in CHAMPIONS.values():
        print(f"  {c.icon} {c.name} ({c.tag}) - {'/'.join(c.roles)}")
        for a in c.abilities:
            print(f"      [{a.ability_type:>8}] {a.name}")
