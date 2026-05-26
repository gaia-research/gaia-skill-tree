from gaia_cli.leveling import demerit_penalty, effective_level, level_summary


def test_effective_level_drops_one_rank_per_demerit():
    skill = {
        "id": "voice-agent",
        "level": "3★",
        "demerits": ["heavyweight-dependency"],
    }
    assert demerit_penalty(skill) == 1
    assert effective_level(skill) == "2★"


def test_effective_level_floors_at_level_zero():
    skill = {
        "id": "workflow-orchestration",
        "level": "2★",
        "demerits": ["niche-integration", "experimental-feature"],
    }
    assert demerit_penalty(skill) == 2
    assert effective_level(skill) == "0★"


def test_level_summary_uses_base_and_effective_levels():
    skill = {
        "id": "mcp-integration",
        "level": "3★",
        "demerits": ["niche-integration"],
    }
    assert level_summary(skill) == {
        "baseLevel": "3★",
        "effectiveLevel": "2★",
        "demerits": ["niche-integration"],
    }


def test_level_one_can_be_demoted_to_zero():
    skill = {
        "id": "tokenize",
        "level": "1★",
        "demerits": ["niche-integration"],
    }
    assert effective_level(skill) == "0★"
