"""LLM validator — RAG-enhanced validation with strict structured output."""
import json
from typing import Optional

from openai import AzureOpenAI
from app.config import settings
from app.domain.enums import IssueSeverity, IssueSource
from app.utils.logging import logger


VALIDATION_PROMPT_V1 = """You are a professional website content validator.

Analyze the following page content chunk for grammar, spelling, style, tone, and brand compliance issues.

{rules_context}

Content to validate (heading path: {heading_path}):
---
{content}
---

For each issue found, provide:
- category: grammar | spelling | style | brand_compliance | readability | formatting | content
- type: specific type (e.g., subject_verb_agreement, passive_voice, inconsistent_tone)
- severity: high | medium | low
- evidence: exact text snippet showing the issue (max 100 chars)
- explanation: why this is an issue
- proposed_fix: suggested correction
- guideline_rule_id: the rule_id from the guidelines if applicable, or null
- confidence: 0.55 to 0.85

Respond with a JSON object: {{"issues": [...]}}
If no issues found, respond with: {{"issues": []}}"""


class LLMValidator:
    """LLM-powered content validation with RAG-enhanced guideline matching."""

    def __init__(self, guideline_rules: list = None):
        self.client = AzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version=settings.API_VERSION,
            azure_endpoint=settings.AZURE_ENDPOINT,
        )
        self.model = settings.MODEL_NAME
        self.guideline_rules = guideline_rules or []

    def validate_chunks(
        self,
        page_url: str,
        chunks: list[dict],
        rag_service=None,
    ) -> list[dict]:
        """
        Validate all chunks for a page using LLM.
        Each chunk: {heading_path, content}
        Returns list of issue dicts.
        """
        all_issues = []

        for chunk in chunks:
            heading = chunk.get("heading_path", "")
            content = chunk.get("content", "")

            if not content or len(content.strip()) < 20:
                continue

            # Get relevant rules via RAG if available
            rules_context = ""
            if rag_service:
                relevant_rules = rag_service.retrieve(content, top_n=5)
                if relevant_rules:
                    rules_text = "\n".join([
                        f"- [{r.get('rule_id', 'N/A')}] {r.get('rule_text', '')}"
                        for r in relevant_rules
                    ])
                    rules_context = f"Apply these specific guideline rules where applicable:\n{rules_text}"
            elif self.guideline_rules:
                # Use all rules if no RAG
                rules_text = "\n".join([
                    f"- [{getattr(r, 'rule_id', 'N/A')}] {getattr(r, 'rule_text', str(r))}"
                    for r in self.guideline_rules[:20]
                ])
                rules_context = f"Apply these specific guideline rules where applicable:\n{rules_text}"

            prompt = VALIDATION_PROMPT_V1.format(
                rules_context=rules_context,
                heading_path=heading or "(root)",
                content=content[:3000],
            )

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a content validator. Always respond with valid JSON format."},
                        {"role": "user", "content": prompt},
                    ],
                )

                response_content = response.choices[0].message.content
                
                # Robust JSON extraction
                if "```json" in response_content:
                    response_content = response_content.split("```json")[-1].split("```")[0].strip()
                elif "```" in response_content:
                    response_content = response_content.split("```")[-2].strip()

                result = json.loads(response_content)
                issues = result.get("issues", [])

                for issue in issues:
                    # Normalize and add source
                    severity = issue.get("severity", "medium").lower()
                    if severity not in ("high", "medium", "low"):
                        severity = "medium"

                    confidence = float(issue.get("confidence", 0.65))
                    # Boost confidence if multiple rules support the finding
                    if issue.get("guideline_rule_id"):
                        confidence = min(confidence + 0.1, 0.85)

                    all_issues.append({
                        "category": issue.get("category", "content"),
                        "type": issue.get("type", "general"),
                        "severity": severity,
                        "evidence": issue.get("evidence", ""),
                        "explanation": issue.get("explanation", ""),
                        "proposed_fix": issue.get("proposed_fix", ""),
                        "guideline_rule_id": issue.get("guideline_rule_id"),
                        "source": IssueSource.LLM,
                        "confidence": confidence,
                    })

            except json.JSONDecodeError as e:
                logger.error(f"LLM response parse error: {e}")
            except Exception as e:
                logger.error(f"LLM validation error for chunk: {e}")

        return all_issues
