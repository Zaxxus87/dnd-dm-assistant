from app.utils.npc_parser import parse_npc_text

sample = """Personality Traits:
*   **Intellectually Curious:** Driven by knowledge.
*   **Methodical:** Careful and planned.

Abilities:
*   **Fey Ancestry:** Advantage on saves.
*   **Trance:** Meditates for 4 hours.

Actions:
*   **Dagger:** Melee Weapon Attack: +5 to hit."""

parsed = parse_npc_text(sample)
print("Personality Traits:")
print(parsed.get('personality_traits', 'Not found'))
print("\nAbilities:")
print(parsed.get('abilities', 'Not found'))
print("\nActions:")
print(parsed.get('actions', 'Not found'))
