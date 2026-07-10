from app.services.user_memory_profile_service import UserMemoryProfileService


def test_mastery_prompt_tolerates_invalid_persisted_scores() -> None:
    service = UserMemoryProfileService()

    result = service._format_mastery_for_prompt(
        {
            "mastery_map": {
                "SQL": "0.8",
                "索引": "invalid",
                "事务": "NaN",
            }
        }
    )

    assert "SQL:80%" in result
    assert "索引:52%" in result
    assert "事务:52%" in result
