"""Tests fuer API-Key/Token Health Checks (domain/api_health.py)."""

import base64
import json

from ti_radar.domain.api_health import check_jwt_expiry, detect_runtime_failures


def _make_jwt(exp: float) -> str:
    """Erzeugt ein minimales JWT mit gegebenem exp-Zeitstempel."""
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256"}).encode()
    ).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": exp}).encode()
    ).decode().rstrip("=")
    return f"{header}.{payload}.fake_signature"


class TestCheckJwtExpiry:
    """Tests fuer JWT-Token-Ablaufpruefung."""

    def test_expired_token_returns_error(self):
        now = 1700000000.0
        token = _make_jwt(exp=now - 3600)
        alert = check_jwt_expiry(token, "OpenAIRE", now=now)
        assert alert is not None
        assert alert.level == "error"
        assert "abgelaufen" in alert.message

    def test_expiring_in_hours_returns_warning(self):
        now = 1700000000.0
        token = _make_jwt(exp=now + 7200)  # 2h
        alert = check_jwt_expiry(token, "OpenAIRE", now=now)
        assert alert is not None
        assert alert.level == "warning"
        assert "Stunden" in alert.message

    def test_expiring_in_days_returns_warning(self):
        now = 1700000000.0
        token = _make_jwt(exp=now + 2 * 24 * 3600)  # 2 Tage
        alert = check_jwt_expiry(token, "OpenAIRE", now=now)
        assert alert is not None
        assert alert.level == "warning"
        assert "Tagen" in alert.message

    def test_valid_token_returns_none(self):
        now = 1700000000.0
        token = _make_jwt(exp=now + 30 * 24 * 3600)  # 30 Tage
        alert = check_jwt_expiry(token, "OpenAIRE", now=now)
        assert alert is None

    def test_exactly_3_days_returns_none(self):
        now = 1700000000.0
        token = _make_jwt(exp=now + 4 * 24 * 3600)  # 4 Tage
        alert = check_jwt_expiry(token, "OpenAIRE", now=now)
        assert alert is None

    def test_empty_token_returns_none(self):
        assert check_jwt_expiry("", "OpenAIRE") is None

    def test_non_jwt_string_returns_none(self):
        assert check_jwt_expiry("just-an-api-key", "OpenAIRE") is None

    def test_jwt_without_exp_returns_none(self):
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256"}).encode()
        ).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user123"}).encode()
        ).decode().rstrip("=")
        token = f"{header}.{payload}.sig"
        assert check_jwt_expiry(token, "OpenAIRE") is None

    def test_source_name_in_alert(self):
        now = 1700000000.0
        token = _make_jwt(exp=now - 100)
        alert = check_jwt_expiry(token, "MeineAPI", now=now)
        assert alert is not None
        assert "MeineAPI" in alert.source
        assert "MeineAPI" in alert.message


class TestDetectRuntimeFailures:
    """Tests fuer Erkennung von API-Laufzeitfehlern in UC-Warnungen."""

    def test_semantic_scholar_failure(self):
        warnings = ["Semantic Scholar Abfrage fehlgeschlagen: timeout"]
        alerts = detect_runtime_failures(warnings)
        assert len(alerts) == 1
        assert alerts[0].source == "Semantic Scholar"
        assert alerts[0].level == "error"

    def test_gleif_failure(self):
        warnings = ["GLEIF Entity Resolution fehlgeschlagen: 503"]
        alerts = detect_runtime_failures(warnings)
        assert len(alerts) == 1
        assert alerts[0].source == "GLEIF"

    def test_openaire_failure(self):
        warnings = ["Query 'publication_years' fehlgeschlagen: HTTPError"]
        alerts = detect_runtime_failures(warnings)
        assert len(alerts) == 1
        assert alerts[0].source == "OpenAIRE"

    def test_no_api_failures_empty(self):
        warnings = ["Patent-DB nicht verfuegbar — keine Patentdaten"]
        assert detect_runtime_failures(warnings) == []

    def test_multiple_failures(self):
        warnings = [
            "Semantic Scholar Abfrage fehlgeschlagen: timeout",
            "GLEIF Entity Resolution fehlgeschlagen: 503",
        ]
        alerts = detect_runtime_failures(warnings)
        assert len(alerts) == 2

    def test_duplicate_source_deduplicated(self):
        warnings = [
            "Semantic Scholar Abfrage fehlgeschlagen: timeout",
            "Semantic Scholar Abfrage fehlgeschlagen: second error",
        ]
        alerts = detect_runtime_failures(warnings)
        assert len(alerts) == 1

    def test_empty_warnings(self):
        assert detect_runtime_failures([]) == []
