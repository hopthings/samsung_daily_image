#!/usr/bin/env python3
"""Validate generated images against art quality rules using GPT-4o vision."""

import base64
import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("DailyArtApp")


@dataclass
class RuleResult:
    """Result of a single rule evaluation."""
    rule_id: str
    passed: bool
    reason: str
    severity: str


@dataclass
class ValidationResult:
    """Result of validating an image against all rules."""
    passed: bool
    failures: List[RuleResult] = field(default_factory=list)
    warnings: List[RuleResult] = field(default_factory=list)
    all_results: List[RuleResult] = field(default_factory=list)
    error: Optional[str] = None


# Validation rules distilled from the generation prompt.
# Critical rules cause rejection; warning rules are logged only.
VALIDATION_RULES = [
    {
        "id": "full_bleed",
        "description": (
            "The artwork extends to all four edges with no visible borders, "
            "frames, canvas edges, vignettes, or margins. The scene continues "
            "beyond the image boundaries."
        ),
        "severity": "critical",
    },
    {
        "id": "not_meta_image",
        "description": (
            "The image IS the artwork itself. It does NOT depict a painting "
            "hanging on a wall, a canvas on an easel, a framed picture, or any "
            "image-within-an-image. No brick walls, gallery walls, wooden "
            "frames, ornate frames, or mounting hardware are visible."
        ),
        "severity": "critical",
    },
    {
        "id": "no_text",
        "description": (
            "No words, letters, signatures, numbers, or watermarks appear "
            "anywhere in the image."
        ),
        "severity": "critical",
    },
    {
        "id": "muted_colours",
        "description": (
            "Colours are muted and naturalistic, with the slightly greyed "
            "quality of real oil pigments. No oversaturated, neon, or "
            "digitally vivid tones."
        ),
        "severity": "warning",
    },
    {
        "id": "palette_knife_style",
        "description": (
            "The artwork shows visible palette knife strokes and thick impasto "
            "texture consistent with oil painting."
        ),
        "severity": "warning",
    },
]


class ImageValidator:
    """Validates generated images against art quality rules using GPT-4o vision."""

    def __init__(self) -> None:
        """Initialize the validator with OpenAI API credentials."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

    def _encode_image(self, image_path: str) -> str:
        """Read and base64-encode an image file.

        Args:
            image_path: Path to the image file.

        Returns:
            Base64-encoded string of the image.
        """
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _build_validation_prompt(self) -> str:
        """Build the validation prompt from the rules list.

        Returns:
            Formatted validation prompt string.
        """
        rules_text = ""
        for i, rule in enumerate(VALIDATION_RULES, 1):
            rules_text += f"{i}. {rule['id'].upper()}: {rule['description']}\n"

        return (
            "You are an art quality reviewer for images displayed on a Samsung "
            "Frame TV. Examine this image carefully and evaluate it against "
            "EACH rule below. For each rule, respond with \"pass\" or \"fail\" "
            "and a brief reason (one sentence).\n\n"
            "Be strict about the critical rules (full_bleed, not_meta_image, "
            "no_text). These are hard requirements. When in doubt, FAIL the "
            "rule. It is better to reject a borderline image than to accept "
            "one that looks like a photo of a painting.\n\n"
            f"Rules:\n{rules_text}\n"
            "Respond ONLY with valid JSON in this exact format:\n"
            "{\n"
            "  \"full_bleed\": {\"result\": \"pass\", \"reason\": \"...\"},\n"
            "  \"not_meta_image\": {\"result\": \"pass\", \"reason\": \"...\"},\n"
            "  \"no_text\": {\"result\": \"pass\", \"reason\": \"...\"},\n"
            "  \"muted_colours\": {\"result\": \"pass\", \"reason\": \"...\"},\n"
            "  \"palette_knife_style\": {\"result\": \"pass\", \"reason\": \"...\"}\n"
            "}"
        )

    def validate(self, image_path: str) -> ValidationResult:
        """Validate an image against the art quality rules.

        Args:
            image_path: Path to the image file to validate.

        Returns:
            ValidationResult with pass/fail status and details.
        """
        try:
            image_b64 = self._encode_image(image_path)
        except (OSError, IOError) as e:
            logger.error(f"Could not read image for validation: {e}")
            return ValidationResult(
                passed=True,
                error=f"Could not read image: {e}",
            )

        # Determine MIME type from extension
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._build_validation_prompt(),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        }

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            results = json.loads(content)

            return self._parse_results(results)

        except requests.exceptions.RequestException as e:
            logger.error(f"Validation API call failed: {e}")
            # On API error, pass the image through — don't block the pipeline
            return ValidationResult(
                passed=True,
                error=f"Validation API error: {e}",
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Could not parse validation response: {e}")
            return ValidationResult(
                passed=True,
                error=f"Validation parse error: {e}",
            )

    def _parse_results(self, results: dict) -> ValidationResult:
        """Parse GPT-4o JSON response into a ValidationResult.

        Args:
            results: Parsed JSON dict from GPT-4o.

        Returns:
            ValidationResult with categorized rule outcomes.
        """
        failures: List[RuleResult] = []
        warnings: List[RuleResult] = []
        all_results: List[RuleResult] = []

        for rule in VALIDATION_RULES:
            rule_id = rule["id"]
            severity = rule["severity"]

            rule_data = results.get(rule_id)
            if rule_data is None:
                logger.warning(
                    f"Validation response missing rule: {rule_id}"
                )
                rule_data = {}
            result_str = rule_data.get("result", "pass").lower().strip()
            reason = rule_data.get("reason", "No reason provided")
            passed = result_str == "pass"

            rule_result = RuleResult(
                rule_id=rule_id,
                passed=passed,
                reason=reason,
                severity=severity,
            )
            all_results.append(rule_result)

            if not passed:
                if severity == "critical":
                    failures.append(rule_result)
                else:
                    warnings.append(rule_result)

        # Image passes only if no critical failures
        overall_passed = len(failures) == 0

        return ValidationResult(
            passed=overall_passed,
            failures=failures,
            warnings=warnings,
            all_results=all_results,
        )
