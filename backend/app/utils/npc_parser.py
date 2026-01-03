import re

def parse_npc_text(text: str) -> dict:
    """Parse the generated NPC text into structured data for the template"""
    data = {}
    
    # Extract basic info
    name_match = re.search(r'NPC Name:\s*(.+?)(?:\n|$)', text)
    if name_match:
        data['name'] = name_match.group(1).strip()
    
    race_match = re.search(r'Race:\s*(.+?)(?:\n|$)', text)
    if race_match:
        data['race'] = race_match.group(1).strip()
    
    class_match = re.search(r'Class:\s*(.+?)(?:\n|$)', text)
    if class_match:
        data['class'] = class_match.group(1).strip()
    
    alignment_match = re.search(r'Alignment:\s*(.+?)(?:\n|$)', text)
    if alignment_match:
        data['alignment'] = alignment_match.group(1).strip()
    
    level_match = re.search(r'Level:\s*(.+?)(?:\n|$)', text)
    if level_match:
        data['level'] = level_match.group(1).strip()
    
    # Extract World Placement
    world_match = re.search(r'World Placement:\s*(.+?)(?:\n\n|\nPhysical)', text, re.DOTALL)
    if world_match:
        data['world_placement'] = world_match.group(1).strip()
    
    # Extract Physical Description
    phys_match = re.search(r'Physical Description:\s*(.+?)(?:\n\n|\nVoice)', text, re.DOTALL)
    if phys_match:
        data['physical_description'] = phys_match.group(1).strip()
    
    # Extract Voice Suggestions
    voice_match = re.search(r'Voice Suggestions:\s*(.+?)(?:\n\n|\nPersonality)', text, re.DOTALL)
    if voice_match:
        data['voice_suggestions'] = voice_match.group(1).strip()
    
    # Extract and format Personality Traits
    personality_match = re.search(r'Personality Traits:\s*(.+?)(?:\n\n|\nBackground)', text, re.DOTALL)
    if personality_match:
        traits_text = personality_match.group(1).strip()
        traits_text = re.sub(r'\*\s+\*\*', '• ', traits_text)
        traits_text = traits_text.replace('**', '')
        data['personality_traits'] = traits_text
    
    # Extract Background
    background_match = re.search(r'Background:\s*(.+?)(?:\n\n|\nStr:|Stat Block)', text, re.DOTALL)
    if background_match:
        data['background'] = background_match.group(1).strip()
    
    # Extract Stats
    str_match = re.search(r'Str:\s*(\d+)', text)
    if str_match:
        data['str'] = str_match.group(1)
    
    dex_match = re.search(r'Dex:\s*(\d+)', text)
    if dex_match:
        data['dex'] = dex_match.group(1)
    
    con_match = re.search(r'Con:\s*(\d+)', text)
    if con_match:
        data['con'] = con_match.group(1)
    
    int_match = re.search(r'Int:\s*(\d+)', text)
    if int_match:
        data['int'] = int_match.group(1)
    
    wis_match = re.search(r'Wis:\s*(\d+)', text)
    if wis_match:
        data['wis'] = wis_match.group(1)
    
    cha_match = re.search(r'Cha:\s*(\d+)', text)
    if cha_match:
        data['cha'] = cha_match.group(1)
    
    # Extract Saving Throws
    saves_match = re.search(r'Saving Throws:\s*(.+?)(?:\n|$)', text)
    if saves_match:
        data['saving_throws'] = saves_match.group(1).strip()
    
    # Extract Skills
    skills_match = re.search(r'Skills:\s*(.+?)(?:\n|$)', text)
    if skills_match:
        data['skills'] = skills_match.group(1).strip()
    
    # Extract Senses
    senses_match = re.search(r'Senses:\s*(.+?)(?:\n|$)', text)
    if senses_match:
        data['senses'] = senses_match.group(1).strip()
    
    # Extract Languages
    lang_match = re.search(r'Languages:\s*(.+?)(?:\n|$)', text)
    if lang_match:
        data['languages'] = lang_match.group(1).strip()
    
    # Extract and format Abilities
    abilities_match = re.search(r'Abilities:\s*(.+?)(?:\n\n|\nActions:)', text, re.DOTALL)
    if abilities_match:
        abilities_text = abilities_match.group(1).strip()
        abilities_text = re.sub(r'\*\s+\*\*', '• ', abilities_text)
        abilities_text = abilities_text.replace('**', '')
        data['abilities'] = abilities_text
    
    # Extract and format Actions
    actions_match = re.search(r'Actions:\s*(.+?)$', text, re.DOTALL)
    if actions_match:
        actions_text = actions_match.group(1).strip()
        actions_text = re.sub(r'\*\s+\*\*', '• ', actions_text)
        actions_text = actions_text.replace('**', '')
        data['actions'] = actions_text
    
    return data
