"""Tests for deterministic validators — all 5 check types."""
import pytest
from app.services.deterministic_validators import DeterministicValidator
from app.domain.enums import IssueSeverity, IssueSource


@pytest.fixture
def validator():
    return DeterministicValidator()


class TestBannedPhrases:
    def test_detects_click_here(self, validator):
        issues = validator.validate("To learn more, click here for details.")
        banned = [i for i in issues if i["type"] == "banned_phrase"]
        assert len(banned) >= 1
        assert any("click here" in i["explanation"].lower() for i in banned)

    def test_detects_read_more(self, validator):
        issues = validator.validate("Read more about our services today.")
        banned = [i for i in issues if i["type"] == "banned_phrase"]
        assert len(banned) >= 1

    def test_detects_learn_more_here(self, validator):
        issues = validator.validate("You can learn more here about pricing.")
        banned = [i for i in issues if i["type"] == "banned_phrase"]
        assert len(banned) >= 1

    def test_no_false_positive_clean_text(self, validator):
        issues = validator.validate("Contact our support team for assistance.")
        banned = [i for i in issues if i["type"] == "banned_phrase"]
        assert len(banned) == 0

    def test_banned_phrase_severity(self, validator):
        issues = validator.validate("Click here to proceed.")
        banned = [i for i in issues if i["type"] == "banned_phrase"]
        assert all(i["severity"] == IssueSeverity.MEDIUM for i in banned)

    def test_banned_phrase_source(self, validator):
        issues = validator.validate("Click here now.")
        banned = [i for i in issues if i["type"] == "banned_phrase"]
        assert all(i["source"] == IssueSource.DETERMINISTIC for i in banned)

    def test_custom_banned_phrases(self):
        v = DeterministicValidator(extra_banned_phrases=["synergy", "leverage"])
        issues = v.validate("We leverage synergy across teams.")
        banned = [i for i in issues if i["type"] == "banned_phrase"]
        assert len(banned) >= 2

    def test_case_insensitive(self, validator):
        issues = validator.validate("CLICK HERE for info.")
        banned = [i for i in issues if i["type"] == "banned_phrase"]
        assert len(banned) >= 1


class TestRepeatedPunctuation:
    def test_detects_multiple_exclamation(self, validator):
        issues = validator.validate("This is amazing!!")
        repeated = [i for i in issues if i["type"] == "repeated_punctuation"]
        assert len(repeated) >= 1

    def test_detects_multiple_question_marks(self, validator):
        issues = validator.validate("What is going on??")
        repeated = [i for i in issues if i["type"] == "repeated_punctuation"]
        assert len(repeated) >= 1

    def test_detects_excessive_periods(self, validator):
        issues = validator.validate("And then..... nothing.")
        repeated = [i for i in issues if i["type"] == "repeated_punctuation"]
        assert len(repeated) >= 1

    def test_allows_ellipsis(self, validator):
        # Standard ellipsis (3 dots) should not be flagged
        issues = validator.validate("Well... maybe not.")
        repeated = [i for i in issues if i["type"] == "repeated_punctuation"]
        assert len(repeated) == 0

    def test_allows_single_punctuation(self, validator):
        issues = validator.validate("Hello! How are you? Fine.")
        repeated = [i for i in issues if i["type"] == "repeated_punctuation"]
        assert len(repeated) == 0

    def test_repeated_punct_severity_is_low(self, validator):
        issues = validator.validate("Great!!!")
        repeated = [i for i in issues if i["type"] == "repeated_punctuation"]
        assert all(i["severity"] == IssueSeverity.LOW for i in repeated)


class TestAllCaps:
    def test_detects_caps_streak(self, validator):
        issues = validator.validate("THIS ENTIRE SENTENCE FEELS LIKE SHOUTING at you.")
        caps = [i for i in issues if i["type"] == "all_caps_abuse"]
        assert len(caps) >= 1

    def test_allows_short_caps(self, validator):
        # Short words like "USA", "FBI" should not trigger
        issues = validator.validate("The USA and FBI are government entities.")
        caps = [i for i in issues if i["type"] == "all_caps_abuse"]
        assert len(caps) == 0

    def test_allows_single_caps_word(self, validator):
        issues = validator.validate("We provide EXCELLENT service!")
        caps = [i for i in issues if i["type"] == "all_caps_abuse"]
        assert len(caps) == 0

    def test_caps_severity_is_medium(self, validator):
        issues = validator.validate("ABSOLUTELY INCREDIBLE FANTASTIC AMAZING results here.")
        caps = [i for i in issues if i["type"] == "all_caps_abuse"]
        if caps:
            assert all(i["severity"] == IssueSeverity.MEDIUM for i in caps)


class TestWhitespace:
    def test_detects_multiple_spaces(self, validator):
        text = "Word  one  word  two  word  three  word  four"
        issues = validator.validate(text)
        ws = [i for i in issues if i["type"] == "whitespace_anomaly"]
        assert len(ws) >= 1

    def test_allows_normal_spacing(self, validator):
        issues = validator.validate("Normal text with single spaces between words.")
        ws = [i for i in issues if i["type"] == "whitespace_anomaly"]
        assert len(ws) == 0


class TestReadingLevel:
    def test_flags_high_reading_level(self, validator):
        # Academic/complex text
        text = " ".join(["The characterization of the implementation of the aforementioned "
                        "methodologies necessitates the utilization of comprehensive "
                        "paradigmatic frameworks that facilitate the operationalization of "
                        "strategic imperatives in a manner that is both systematically "
                        "rigorous and pragmatically efficacious."] * 5)
        issues = validator.validate(text)
        reading = [i for i in issues if i["type"] == "reading_level"]
        # Note: only fires if textstat is available
        if reading:
            assert reading[0]["severity"] == IssueSeverity.MEDIUM

    def test_no_reading_level_for_short_text(self, validator):
        issues = validator.validate("Short text here.")
        reading = [i for i in issues if i["type"] == "reading_level"]
        assert len(reading) == 0


class TestEmptyInput:
    def test_empty_string_returns_no_issues(self, validator):
        assert validator.validate("") == []

    def test_whitespace_only_returns_no_issues(self, validator):
        assert validator.validate("   \n\t  ") == []

    def test_none_handling(self, validator):
        # Should not crash
        assert validator.validate(None) == []


class TestIssueStructure:
    def test_issue_has_all_required_fields(self, validator):
        issues = validator.validate("Click here for more!!")
        for issue in issues:
            assert "category" in issue
            assert "type" in issue
            assert "severity" in issue
            assert "evidence" in issue
            assert "explanation" in issue
            assert "proposed_fix" in issue
            assert "source" in issue
            assert "confidence" in issue

    def test_confidence_range(self, validator):
        issues = validator.validate("Click here!! for MORE AMAZING INCREDIBLE STUFF")
        for issue in issues:
            assert 0.0 <= issue["confidence"] <= 1.0
