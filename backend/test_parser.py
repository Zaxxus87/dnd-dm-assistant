from app.utils.npc_parser import parse_npc_text

# Your example text from earlier
sample_text = """NPC Name: Elara Meadowbrook
Race: High Elf
Class: Wizard (School of Abjuration)
Alignment: Neutral Good
Level: 5
World Placement: Elara serves as the principal archivist and magical consultant within the Grand Library of Silverhaven.

Physical Description: Elara possesses the characteristic slender grace of a high elf, standing at 5'6" with an elegant posture.

Voice Suggestions: Her voice is soft, melodic, and precise.

Personality Traits:
*   **Intellectually Curious:** Driven by an insatiable thirst for knowledge.
*   **Methodical and Prudent:** Approaches problems with careful consideration.

Background: Elara was raised in a reclusive elven conclave known for its ancient magical libraries.

Str: 8
Dex: 16
Con: 13
Int: 16
Wis: 12
Cha: 10

Saving Throws: Intelligence (+6), Wisdom (+3)
Skills: Arcana (+6), History (+6), Investigation (+6), Perception (+3)
Senses: Passive Perception 13, Darkvision 60 ft.
Languages: Common, Elvish, Draconic, Sylvan

Abilities:
*   **Fey Ancestry:** Elara has advantage on saving throws.

Actions:
*   **Dagger:** Melee Weapon Attack: +5 to hit.
*   **Fire Bolt:** Ranged Spell Attack: +6 to hit."""

parsed = parse_npc_text(sample_text)

print("Parsed Data:")
for key, value in parsed.items():
    print(f"\n{key}: {value[:100] if len(str(value)) > 100 else value}")
