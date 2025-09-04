import numpy as np
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum

class RollDirection(Enum):
    MATCH = "match"      # >= target (default behavior)
    ABOVE = "above"      # > target (strictly exceed)
    BELOW = "below"      # < target (below target)

def roll_dice(num_dice: int, target: int, 
              rng: Optional[np.random.Generator] = None,
              direction: Union[RollDirection, str] = RollDirection.MATCH,
              critical_count: bool = False, 
              critical_threshold: int = 6) -> Union[int, Tuple[int, int]]:
    """Rolls a number of dice and counts number that match criteria"""
    
    if rng is None:
        rng = np.random.default_rng()
    
    # Convert string to enum if needed
    if isinstance(direction, str):
        direction = RollDirection(direction.lower())
    
    rolls = rng.integers(1, 7, size=num_dice)

    if direction == RollDirection.MATCH:
        hits = np.sum(rolls >= target)
    elif direction == RollDirection.ABOVE:
        hits = np.sum(rolls > target)
    elif direction == RollDirection.BELOW:
        hits = np.sum(rolls < target)
    
    # Return critical count if requested
    if critical_count:
        crits = np.sum(rolls >= critical_threshold)
        return hits, crits

    return hits

class AttackOrder(Enum):
    DETERMINISTIC = "deterministic"
    PROBABILISTIC = "probabilistic"

@dataclass
class Unit:
    name: str
    models: int
    wounds_per_model: int
    save: int
    ward_save: int = 7
    ethereal: bool = False
    beacon_of_protection: bool = False
    weapons: List['Weapon'] = None
    has_leader: bool = True
    unit_alive: bool = True
    
    def __post_init__(self):
        """Calculate total_wounds once after initialization"""
        self.total_wounds = self.models * self.wounds_per_model

    def take_damage(self, damage: int, rend: int=0, mortal: bool = False, ward_ignore: bool = False):
        #takes a number of wounds done as an input, runs this against the unit's defensive statistics, updates models and total_wounds

        if mortal:
            wounds_through_save = damage
        elif self.ethereal:
            wounds_through_save = roll_dice(damage, self.save, direction="below")
        else:
            wounds_through_save = roll_dice(damage, self.save + rend, direction="below")

        if self.ward_save and not ward_ignore:
            wounds_through_save = roll_dice(wounds_through_save, self.ward_save, direction="below")

        if self.beacon_of_protection:
            wounds_through_save = max(0, wounds_through_save - 1)

        self.total_wounds -= wounds_through_save
        
        # Update models count (each model needs at least 1 wound to survive)
        full_models = self.total_wounds // self.wounds_per_model
        has_partial_model = 1 if self.total_wounds % self.wounds_per_model > 0 else 0
        self.models = max(0, full_models + has_partial_model)

        if self.models <= 0:
            self.unit_alive = False

        return wounds_through_save

    def deal_damage(self, hit_modifier: int = 0, wound_modifier: int = 0):
        """Performs the attack process for all weapons, returning list of damage tuples"""
        
        damage_list = []

        for weapon in self.weapons:
            weapon_attacks = weapon.attacks * self.models
            if self.has_leader and not weapon.companion:
                weapon_attacks += 1
            
            # Hit sequence
            if weapon.crit_explode:
                attacks_landed, crits = roll_dice(num_dice=weapon_attacks, target=weapon.to_hit - hit_modifier, direction="match", critical_count=True, critical_threshold=weapon.crit_threshold)
                attacks_landed += crits  
            elif weapon.crit_mortals:
                attacks_landed, crits = roll_dice(num_dice=weapon_attacks, target=weapon.to_hit - hit_modifier, direction="match", critical_count=True, critical_threshold=weapon.crit_threshold)
                # Add mortal damage from crits
                if crits > 0:
                    damage_list.append((crits * weapon.damage, 0, "mortal"))
                attacks_landed -= crits
            else:
                attacks_landed = roll_dice(num_dice=weapon_attacks, target=weapon.to_hit - hit_modifier, direction="match")
            
            # Wound sequence
            wounds_landed = roll_dice(num_dice=attacks_landed, target=weapon.to_wound - wound_modifier, direction="match")
            
            # Add normal damage from this weapon
            if wounds_landed > 0:
                damage_list.append((wounds_landed * weapon.damage, weapon.rend, "normal"))
        
        return damage_list

@dataclass
class Weapon:
    name: str
    attacks: int
    to_hit: int
    to_wound: int
    rend: int
    damage: int
    companion: bool = False
    crit_threshold: int = 6
    crit_mortals: bool = False
    crit_explode: bool = False

def load_units_from_json(filepath: str) -> Dict[str, Unit]:
    """Load unit data from JSON file"""
    # Placeholder - you'll implement based on your JSON structure
    pass

def combat_simulation(attacker: Unit, defender: Unit, order_inversion_probability: float = 0, iterations: int = 10000,
    attacker_hit_modifier: int = 0, attacker_wound_modifier: int = 0,
    defender_hit_modifier: int = 0, defender_wound_modifier: int = 0):
    """Simulate combat between 2 units n times, return average remaining wounds from each"""
    
    attacker_wounds_remaining = []
    defender_wounds_remaining = []
    inverted_fights = 0
    
    for _ in range(iterations):
        # Create fresh copies of units for each simulation
        att_copy = Unit(
            name=attacker.name,
            models=attacker.models,
            wounds_per_model=attacker.wounds_per_model,
            save=attacker.save,
            ward_save=attacker.ward_save,
            ethereal=attacker.ethereal,
            beacon_of_protection=attacker.beacon_of_protection,
            weapons=attacker.weapons,
            has_leader=attacker.has_leader
        )
        
        def_copy = Unit(
            name=defender.name,
            models=defender.models,
            wounds_per_model=defender.wounds_per_model,
            save=defender.save,
            ward_save=defender.ward_save,
            ethereal=defender.ethereal,
            beacon_of_protection=defender.beacon_of_protection,
            weapons=defender.weapons,
            has_leader=defender.has_leader
        )
        
        # Determine attack order
        order_roll = np.random.random()
        
        if order_roll < order_inversion_probability:
            inverted_fights += 1
            # Defender attacks first
            if def_copy.unit_alive:
                damage_list = def_copy.deal_damage(hit_modifier=defender_hit_modifier, wound_modifier=defender_wound_modifier)
                for damage, rend, damage_type in damage_list:
                    if damage_type == "mortal":
                        att_copy.take_damage(damage, mortal=True)
                    else:
                        att_copy.take_damage(damage, rend=rend)
            
            # Attacker responds (if still alive)
            if att_copy.unit_alive:
                damage_list = att_copy.deal_damage(hit_modifier=attacker_hit_modifier, wound_modifier=attacker_wound_modifier)
                for damage, rend, damage_type in damage_list:
                    if damage_type == "mortal":
                        def_copy.take_damage(damage, mortal=True)
                    else:
                        def_copy.take_damage(damage, rend=rend)
        else:
            # Attacker attacks first
            if att_copy.unit_alive:
                damage_list = att_copy.deal_damage(hit_modifier=attacker_hit_modifier, wound_modifier=attacker_wound_modifier)
                for damage, rend, damage_type in damage_list:
                    if damage_type == "mortal":
                        def_copy.take_damage(damage, mortal=True)
                    else:
                        def_copy.take_damage(damage, rend=rend)
            
            # Defender responds (if still alive)
            if def_copy.unit_alive:
                damage_list = def_copy.deal_damage(hit_modifier=defender_hit_modifier, wound_modifier=defender_wound_modifier)
                for damage, rend, damage_type in damage_list:
                    if damage_type == "mortal":
                        att_copy.take_damage(damage, mortal=True)
                    else:
                        att_copy.take_damage(damage, rend=rend)
        
        # Record remaining wounds
        attacker_wounds_remaining.append(att_copy.total_wounds)
        defender_wounds_remaining.append(def_copy.total_wounds)
    
    # Return average wounds remaining
    avg_attacker_wounds = np.mean(attacker_wounds_remaining)
    avg_defender_wounds = np.mean(defender_wounds_remaining)
    
    return avg_attacker_wounds, avg_defender_wounds, inverted_fights

# Example usage
if __name__ == "__main__":

    #chaos knight weapons    
    lance = Weapon("Cursed Lance", attacks=3, to_hit=3, to_wound=3, rend=2, damage=1)
    hooves = Weapon("Hooves", attacks=2, to_hit=5, to_wound=3, rend=0, damage=1, companion=True)

    #dawnrider weapons
    impact = Weapon("Impact", attacks=1, to_hit=3, to_wound=1, rend=0, damage=1, crit_mortals=True, crit_threshold=3)
    dawn_lance = Weapon("Dawn Lance", attacks=3, to_hit=3, to_wound=4, rend=1, damage=2, crit_mortals=True)
    dawn_hooves = Weapon("Hooves", attacks=2, to_hit=5, to_wound=3, rend=0, damage=1, companion=True)

    #varanguard
    varan_blade = Weapon("Varan Blade", attacks=3, to_hit=3, to_wound=3, rend=2, damage=3, crit_mortals=True, crit_threshold=6)
    varan_hooves = Weapon("Hooves", attacks=3, to_hit=4, to_wound=3, rend=0, damage=1, companion=True)

    #warden weapons
    pike = Weapon("Pike", attacks=2, to_hit=3, to_wound=4, rend=1, damage=1, crit_mortals=True, crit_threshold=6)

    #bladelord weapons
    blades = Weapon("Blades", attacks=3, to_hit=3, to_wound=4, rend=1, damage=1, crit_mortals=True, crit_threshold=6)

    chaos_knights = Unit("Chaos Knight", models=10, wounds_per_model=4, save=3, weapons=[lance, hooves])
    varanguard = Unit("Varanguard", models=6, wounds_per_model=5, save=3, weapons=[varan_blade, varan_hooves])
    
    dawnriders = Unit("Dawnrider", models=10, wounds_per_model=3, save=3, weapons=[dawn_lance, dawn_hooves, impact], ward_save=5)

    base_wardens = Unit("Warden", models=20, wounds_per_model=1, save=4, weapons=[pike])
    ward_wardens = Unit("Warden", models=20, wounds_per_model=1, save=4, weapons=[pike], ward_save=5)
    mega_wardens = Unit("Warden", models=20, wounds_per_model=1, save=4, weapons=[pike], ward_save=5, ethereal=True)

    bladelords = Unit("Bladelord", models=10, wounds_per_model=2, save=4, weapons=[blades], ward_save=5, ethereal=True)
    mega_bladelords = Unit("Bladelord", models=10, wounds_per_model=2, save=4, weapons=[blades], ward_save=5, ethereal=True, beacon_of_protection=True)

    avg_attacker, avg_defender, inversions = combat_simulation(dawnriders, chaos_knights, order_inversion_probability=0, iterations=10000)
    print(f"Dawnrider counter - dawnrider wounds: {avg_attacker:.2f} chaos knight wounds: {avg_defender:.2f} inversions: {inversions}")

    scenario_atk_hit_mod = -1

    avg_attacker, avg_defender, inversions = combat_simulation(varanguard, base_wardens, order_inversion_probability=4/6, iterations=10000, attacker_hit_modifier=scenario_atk_hit_mod)
    print(f"Base warden scenario - knight wounds: {avg_attacker:.2f} warden wounds: {avg_defender:.2f} inversions: {inversions}")

    avg_attacker, avg_defender, inversions = combat_simulation(varanguard, ward_wardens, order_inversion_probability=4/6, iterations=10000, attacker_hit_modifier=scenario_atk_hit_mod)
    print(f"Ward warden scenario - knight wounds: {avg_attacker:.2f} warden wounds: {avg_defender:.2f} inversions: {inversions}")

    avg_attacker, avg_defender, inversions = combat_simulation(varanguard, mega_wardens, order_inversion_probability=4/6, iterations=10000, attacker_hit_modifier=scenario_atk_hit_mod)
    print(f"Mega warden scenario - knight wounds: {avg_attacker:.2f} warden wounds: {avg_defender:.2f} inversions: {inversions}")

    avg_attacker, avg_defender, inversions = combat_simulation(varanguard, bladelords, iterations=10000, attacker_hit_modifier=scenario_atk_hit_mod)
    print(f"Bladelord scenario - knight wounds: {avg_attacker:.2f} bladelord wounds: {avg_defender:.2f} inversions: {inversions}")

    avg_attacker, avg_defender, inversions = combat_simulation(varanguard, mega_bladelords, iterations=10000, attacker_hit_modifier=scenario_atk_hit_mod)
    print(f"Mega bladelord scenario - knight wounds: {avg_attacker:.2f} bladelord wounds: {avg_defender:.2f} inversions: {inversions}")