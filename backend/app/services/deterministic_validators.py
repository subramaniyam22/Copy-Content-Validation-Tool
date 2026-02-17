"""Deterministic validators — fast, cheap, high-confidence checks."""
import re
from app.domain.enums import IssueSeverity, IssueSource
from app.domain.fingerprints import compute_issue_fingerprint

try:
    import textstat
except ImportError:
    textstat = None


class DeterministicValidator:
    """Run deterministic validation rules against text content."""

    # Default banned phrases (can be extended from guideline rules)
    BANNED_PHRASES = [
        "click here",
        "read more",
        "learn more here",
        "click this link",
    ]

    # Non-descriptive link text patterns
    NON_DESCRIPTIVE_LINK_TEXT = [
        "here", "click", "this", "link", "more", "read more",
    ]

    def __init__(self, extra_banned_phrases: list[str] = None):
        self.banned_phrases = list(self.BANNED_PHRASES)
        if extra_banned_phrases:
            self.banned_phrases.extend(extra_banned_phrases)

    def validate(
        self,
        text: str,
        heading_path: str = "",
        page_url: str = "",
    ) -> list[dict]:
        """Run all deterministic checks on a text chunk. Returns list of issue dicts."""
        issues = []

        if not text or not text.strip():
            return issues

        issues.extend(self._check_banned_phrases(text, heading_path, page_url))
        issues.extend(self._check_repeated_punctuation(text, heading_path, page_url))
        issues.extend(self._check_all_caps(text, heading_path, page_url))
        issues.extend(self._check_whitespace_anomalies(text, heading_path, page_url))
        issues.extend(self._check_reading_level(text, heading_path, page_url))

        return issues

    def _check_banned_phrases(self, text: str, heading_path: str, page_url: str) -> list[dict]:
        issues = []
        text_lower = text.lower()
        for phrase in self.banned_phrases:
            if phrase.lower() in text_lower:
                # Find the evidence snippet
                idx = text_lower.index(phrase.lower())
                start = max(0, idx - 30)
                end = min(len(text), idx + len(phrase) + 30)
                evidence = text[start:end]

                issues.append({
                    "category": "link_text",
                    "type": "banned_phrase",
                    "severity": IssueSeverity.MEDIUM,
                    "evidence": f'...{evidence}...',
                    "explanation": f'The phrase "{phrase}" is non-descriptive and should be replaced with meaningful text.',
                    "proposed_fix": f'Replace "{phrase}" with a descriptive action or destination.',
                    "source": IssueSource.DETERMINISTIC,
                    "confidence": 0.90,
                })
        return issues

    def _check_repeated_punctuation(self, text: str, heading_path: str, page_url: str) -> list[dict]:
        issues = []
        patterns = [
            (r'[!]{2,}', 'Multiple exclamation marks'),
            (r'[?]{2,}', 'Multiple question marks'),
            (r'[.]{4,}', 'Excessive periods (not an ellipsis)'),
            (r'[,]{2,}', 'Multiple consecutive commas'),
        ]
        for pattern, desc in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                evidence = text[start:end]
                issues.append({
                    "category": "formatting",
                    "type": "repeated_punctuation",
                    "severity": IssueSeverity.LOW,
                    "evidence": f'...{evidence}...',
                    "explanation": f'{desc} detected.',
                    "proposed_fix": "Use standard punctuation.",
                    "source": IssueSource.DETERMINISTIC,
                    "confidence": 0.95,
                })
        return issues

    def _check_all_caps(self, text: str, heading_path: str, page_url: str) -> list[dict]:
        issues = []
        # Find words that are all caps and longer than 3 chars (not acronyms)
        words = text.split()
        caps_streak = []
        for word in words:
            clean = re.sub(r'[^A-Za-z]', '', word)
            if clean and len(clean) > 3 and clean.isupper():
                caps_streak.append(word)
            else:
                if len(caps_streak) >= 3:
                    evidence = ' '.join(caps_streak)
                    issues.append({
                        "category": "formatting",
                        "type": "all_caps_abuse",
                        "severity": IssueSeverity.MEDIUM,
                        "evidence": evidence,
                        "explanation": "Excessive use of ALL CAPS can feel like shouting and reduces readability.",
                        "proposed_fix": "Use title case or sentence case instead.",
                        "source": IssueSource.DETERMINISTIC,
                        "confidence": 0.85,
                    })
                caps_streak = []

        # Check remaining streak
        if len(caps_streak) >= 3:
            evidence = ' '.join(caps_streak)
            issues.append({
                "category": "formatting",
                "type": "all_caps_abuse",
                "severity": IssueSeverity.MEDIUM,
                "evidence": evidence,
                "explanation": "Excessive use of ALL CAPS can feel like shouting and reduces readability.",
                "proposed_fix": "Use title case or sentence case instead.",
                "source": IssueSource.DETERMINISTIC,
                "confidence": 0.85,
            })
        return issues

    def _check_whitespace_anomalies(self, text: str, heading_path: str, page_url: str) -> list[dict]:
        issues = []
        # Multiple spaces
        double_spaces = list(re.finditer(r'[^ \n]  +[^ \n]', text))
        if len(double_spaces) > 2:
            issues.append({
                "category": "formatting",
                "type": "whitespace_anomaly",
                "severity": IssueSeverity.LOW,
                "evidence": f"Found {len(double_spaces)} instances of multiple consecutive spaces",
                "explanation": "Multiple consecutive spaces may indicate copy-paste issues or formatting problems.",
                "proposed_fix": "Replace multiple spaces with single spaces.",
                "source": IssueSource.DETERMINISTIC,
                "confidence": 0.80,
            })
        return issues

    def _check_reading_level(self, text: str, heading_path: str, page_url: str) -> list[dict]:
        issues = []
        if not textstat or len(text.split()) < 50:
            return issues

        try:
            fk_grade = textstat.flesch_kincaid_grade(text)
            if fk_grade > 12:
                issues.append({
                    "category": "readability",
                    "type": "reading_level",
                    "severity": IssueSeverity.MEDIUM,
                    "evidence": f"Flesch-Kincaid Grade Level: {fk_grade:.1f} (section: {heading_path or 'page'})",
                    "explanation": f"Content reads at a grade {fk_grade:.1f} level. Web content should target grade 8-10 for maximum accessibility.",
                    "proposed_fix": "Simplify sentence structure and use shorter, more common words.",
                    "source": IssueSource.DETERMINISTIC,
                    "confidence": 0.80,
                })
        except Exception:
            pass

        return issues
