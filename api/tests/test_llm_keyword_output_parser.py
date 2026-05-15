import pytest

from app.models.enums import KeywordCategory
from app.services.keywords.output_parser import KeywordOutputParseError, parse_keyword_output


def test_parser_accepts_valid_schema() -> None:
    result = parse_keyword_output(
        '{"keywords":[{"text":"쉼","normalized":"쉼","category":"recovery","weight":1.0}]}'
    )

    assert len(result) == 1
    assert result[0].normalized == "쉼"
    assert result[0].category == KeywordCategory.RECOVERY.value


def test_parser_allows_empty_keywords_array() -> None:
    assert parse_keyword_output('{"keywords":[]}') == []


def test_parser_normalizes_unknown_category_to_neutral() -> None:
    result = parse_keyword_output(
        '{"keywords":[{"text":"맑음","normalized":"맑음","category":"bad","weight":1.0}]}'
    )

    assert result[0].category == KeywordCategory.NEUTRAL.value


def test_parser_rejects_non_numeric_weight() -> None:
    with pytest.raises(KeywordOutputParseError):
        parse_keyword_output(
            '{"keywords":[{"text":"쉼","normalized":"쉼","category":"recovery","weight":"heavy"}]}'
        )


def test_parser_limits_keywords_to_five() -> None:
    result = parse_keyword_output(
        '{"keywords":['
        '{"text":"긴장","normalized":"긴장","category":"mind_signal","weight":1},'
        '{"text":"감사","normalized":"감사","category":"support","weight":1},'
        '{"text":"회복","normalized":"회복","category":"recovery","weight":1},'
        '{"text":"호흡","normalized":"호흡","category":"recovery","weight":1},'
        '{"text":"산책","normalized":"산책","category":"coping","weight":1},'
        '{"text":"응원","normalized":"응원","category":"support","weight":1}'
        "]}",
    )

    assert len(result) == 5


def test_parser_raises_on_invalid_json() -> None:
    with pytest.raises(KeywordOutputParseError):
        parse_keyword_output("not-json")
