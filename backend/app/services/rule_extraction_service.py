"""Rule extraction service — use LLM to extract structured rules from guideline text."""
import json
from typing import Optional

from openai import AzureOpenAI
from app.config import settings
from app.utils.logging import logger


RULE_EXTRACTION_PROMPT_V1 = """You are a content compliance rules extraction expert.

Analyze the following style guide / brand guidelines text and extract ALL actionable rules.
The text contains markers like "=== filename.pdf ===" indicating where each file begins.

For each rule, output a JSON object with these fields:
- rule_id: a short stable identifier like "STYLE-001", "GRAMMAR-002", etc.
- category: one of "grammar", "spelling", "style", "brand_compliance", "formatting", "readability", "content"
- type: specific rule type (e.g., "capitalization", "banned_phrase", "tone", "punctuation")
- severity_default: "high", "medium", or "low"
- rule_text: the full rule description
- fix_template: suggested fix pattern (if applicable)
- examples_good: example of correct usage (if available)
- examples_bad: example of incorrect usage (if available)
- source_file: the filename (from the === markers) this rule belongs to
- section_ref: section/page reference from the original document

Output ONLY a JSON array of rule objects. No other text.

Guidelines text:
{guidelines_text}"""

PROMPT_VERSION = "rule_extraction_v1"


class RuleExtractionService:
    """Extract structured rules from guideline text using LLM."""

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version=settings.API_VERSION,
            azure_endpoint=settings.AZURE_ENDPOINT,
        )
        self.model = settings.MODEL_NAME

    def extract_rules(self, guidelines_text: str) -> tuple[list[dict], str, str]:
        """
        Extract rules from guidelines text.
        Returns: (rules_list, prompt_version, model_used)
        """
        if not guidelines_text or len(guidelines_text.strip()) < 50:
            logger.warning("Guidelines text too short for rule extraction")
            return [], PROMPT_VERSION, self.model

        # Truncate if too long (model context limits)
        max_chars = 30000
        if len(guidelines_text) > max_chars:
            guidelines_text = guidelines_text[:max_chars] + "\n\n[... truncated ...]"

        prompt = RULE_EXTRACTION_PROMPT_V1.format(guidelines_text=guidelines_text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You extract structured rules from style guides. Always respond with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content
            
            # Robust JSON extraction (handles markdown blocks)
            if "```json" in content:
                content = content.split("```json")[-1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[-2].strip()

            parsed = json.loads(content)
            
            # Handle both {"rules": [...]} and [...] formats
            if isinstance(parsed, dict):
                rules = parsed.get("rules", [])
            elif isinstance(parsed, list):
                rules = parsed
            else:
                rules = []

            logger.info(f"Extracted {len(rules)} rules from guidelines")
            return rules, PROMPT_VERSION, self.model

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM rule extraction output: {e}. Content: {content[:500]}")
            return [], PROMPT_VERSION, self.model
        except Exception as e:
            logger.error(f"Rule extraction failed: {str(e)}", exc_info=True)
            return [], PROMPT_VERSION, self.model
