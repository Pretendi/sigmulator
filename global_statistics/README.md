This is where I parsed unit statistics from all age of sigmar index pdfs.

Overall parsing structure:
0. Open pdf using PyMuPDF
1. Identify each page type (unit, faction_traits, delete (incl. spearhead))
2. For unit pages, parse relevant text

Outputs are 2 tables:
1. Unit statistics      --> (Faction, Unit, Health, Move, Save, Control)
2. Weapon statistics    --> (Unit, Type, Range, Attacks, To Hit, To Wound, Rend, Damage, Abilities)
3. (WIP) unit abilities (including spells)

Note that annoyingly, warscroll data DOES NOT CONTAIN unit sizes! This will need to be added manually for warscrolls that do not contain clues.