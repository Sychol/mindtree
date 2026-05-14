from app.db.base import Base
from app import models  # noqa: F401


def test_core_tables_registered() -> None:
    expected_tables = {
        "events",
        "sessions",
        "consent_logs",
        "questions",
        "answers",
        "scale_scores",
        "risk_flags",
        "summaries",
        "mind_cards",
        "card_selections",
        "replies",
        "keyword_jobs",
        "keywords",
        "completion_codes",
        "admin_users",
        "admin_audit_logs",
    }

    assert expected_tables.issubset(set(Base.metadata.tables.keys()))


def test_sensitive_raw_session_columns_not_registered() -> None:
    session_columns = set(Base.metadata.tables["sessions"].columns.keys())
    consent_columns = set(Base.metadata.tables["consent_logs"].columns.keys())

    assert "resume_token" not in session_columns
    assert "session_key" not in session_columns
    assert "ip_address" not in consent_columns
    assert "user_agent" not in consent_columns
