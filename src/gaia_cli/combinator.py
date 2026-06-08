from .leveling import effective_level


def transitive_close(graph_data: dict, skill_ids: set) -> set:
    """Expand a set of skill IDs by iteratively unlocking reachable composites.

    Starting from *skill_ids*, any extra/ultimate skill whose every prerequisite
    is already in the expanding set is added.  The process repeats until no new
    skills are discovered (fixpoint).  Cycles are safe because once an id is in
    the expanding set it is never revisited.

    Args:
        graph_data: parsed gaia.json (needs ``skills`` list).
        skill_ids: initial set of owned/detected skill IDs.

    Returns:
        A new set containing *skill_ids* plus all transitively unlockable skills.
    """
    available = set(skill_ids)
    composites = [
        s for s in graph_data.get('skills', [])
        if s.get('type') in ('extra', 'ultimate') and s.get('prerequisites')
    ]
    changed = True
    while changed:
        changed = False
        for skill in composites:
            sid = skill['id']
            if sid in available:
                continue
            if all(p in available for p in skill.get('prerequisites', [])):
                available.add(sid)
                changed = True
    return available


def detect_combinations(graph_data, owned_skills, detected_skills):
    combinations = []

    owned_skill_ids = set()
    for skill in owned_skills:
        if isinstance(skill, dict) and 'skillId' in skill:
            owned_skill_ids.add(skill['skillId'])
        elif isinstance(skill, str):
            owned_skill_ids.add(skill)

    combined_available = owned_skill_ids.union(set(detected_skills))

    # Transitively expand combined_available to find chain-fusion candidates.
    # The expanded set reveals skills that can be unlocked once intermediate
    # composites are fused (even when those intermediates are not yet in
    # combined_available).
    expanded = transitive_close(graph_data, combined_available)

    skill_map = {s['id']: s for s in graph_data.get('skills', [])}

    for skill in graph_data.get('skills', []):
        if skill.get('type') not in ['extra', 'ultimate']:
            continue

        prereqs = skill.get('prerequisites', [])
        if not prereqs:
            continue

        sid = skill['id']
        if sid in owned_skill_ids:
            continue

        direct_satisfied = all(prereq in combined_available for prereq in prereqs)

        if direct_satisfied:
            # Standard direct fusion — unchanged behaviour.
            combinations.append({
                'candidateResult': sid,
                'levelFloor': effective_level(skill),
                'baseLevelFloor': skill.get('level'),
                'detectedSkills': [p for p in prereqs if p in detected_skills] or prereqs,
                'status': 'new_fusion',
            })
        else:
            # Check if sid is reachable via chain by excluding sid itself from available skills.
            # This prevents a scanned composite skill from satisfying its own prerequisites.
            expanded_without_sid = transitive_close(graph_data, combined_available - {sid})
            if sid in expanded_without_sid:
                missing_direct = [p for p in prereqs if p not in combined_available]
                chain_steps = []
                for step_id in missing_direct:
                    step = skill_map.get(step_id)
                    if step and step.get('type') in ('extra', 'ultimate'):
                        chain_steps.append(step_id)
                combinations.append({
                    'candidateResult': sid,
                    'levelFloor': effective_level(skill),
                    'baseLevelFloor': skill.get('level'),
                    'detectedSkills': [p for p in prereqs if p in combined_available] or prereqs,
                    'status': 'chain_fusion',
                    'chainSteps': chain_steps,
                })

    return combinations

def get_combinations(graph_data, owned_skills, detected_skills):
    return detect_combinations(graph_data, owned_skills, detected_skills)
