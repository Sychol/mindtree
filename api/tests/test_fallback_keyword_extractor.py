from app.services.keywords.fallback_extractor import extract_fallback_keywords


def _normalized(text: str) -> set[str]:
    return {
        candidate.normalized
        for candidate in extract_fallback_keywords(
            text,
            source_type="mind_card",
            source_hint="to_now_me",
        )
    }


def test_fallback_extracts_sleep_keywords() -> None:
    assert _normalized("잠이 안 와요") & {"잠", "피로"}


def test_fallback_extracts_tension_keywords() -> None:
    assert _normalized("가슴이 답답해요") & {"답답함", "긴장"}


def test_fallback_extracts_support_and_recovery_keywords() -> None:
    assert _normalized("괜찮아요 쉬어가도 돼요") & {"괜찮아", "쉼"}


def test_fallback_extracts_endurance_keywords() -> None:
    assert _normalized("오늘도 버텼어요") & {"버팀", "회복"}


def test_fallback_extracts_breathing_keywords() -> None:
    assert _normalized("숨을 천천히 쉬어봐요") & {"호흡", "안정"}


def test_fallback_filters_personal_info_and_crisis_terms() -> None:
    keywords = _normalized("연락은 010-1234-5678 이고 자살이라는 말은 빼 주세요.")

    assert "010-1234-5678" not in keywords
    assert "자살" not in keywords


def test_fallback_can_return_empty_for_stopwords_only() -> None:
    assert _normalized("나 너 우리 그냥 정말") == set()
