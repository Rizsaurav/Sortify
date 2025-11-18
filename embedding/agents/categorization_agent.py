"""
Categorization Agent - Lean & Scalable
LLM → Keywords → Default
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

from openai import OpenAI, RateLimitError, APITimeoutError, APIError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration / Result Models
# ---------------------------------------------------------------------------

@dataclass
class CategorizationConfig:
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.3
    llm_timeout: float = 30.0
    llm_max_retries: int = 2
    max_suggestions: int = 3
    min_confidence: float = 0.5
    max_content_length: int = 2000
    enable_keywords: bool = True
    default_category: str = "Uncategorized"


@dataclass
class CategoryResult:
    categories: List[str]
    confidence: float
    source: str
    reasoning: str = ""
    time_ms: float = 0.0
    user_id: Optional[str] = None


class ValidationError(Exception):
    pass


# ---------------------------------------------------------------------------
# Base Layer
# ---------------------------------------------------------------------------

class Layer(ABC):
    @abstractmethod
    def categorize(
        self,
        content: str,
        filename: str,
        user_cats: List[str],
        max_suggestions: int,
        user_id: str,
    ) -> Optional[CategoryResult]:
        pass


# ---------------------------------------------------------------------------
# LLM Layer
# ---------------------------------------------------------------------------

class LLMLayer(Layer):
    def __init__(self, config: CategorizationConfig):
        self.cfg = config
        self.client = OpenAI()

    def categorize(self, content, filename, user_cats, max_suggestions, user_id):
        """Primary LLM categorization with retry logic."""
        delay = 2.0

        for attempt in range(1, self.cfg.llm_max_retries + 1):
            try:
                result = self._call_llm(content, filename, user_cats, max_suggestions, user_id)
                if result and result.confidence >= self.cfg.min_confidence:
                    return result
                return None

            except (RateLimitError, APITimeoutError):
                if attempt < self.cfg.llm_max_retries:
                    time.sleep(delay)
                    delay *= 2
                else:
                    return None
            except Exception as e:
                logger.error(f"LLM error: {e}")
                return None

        return None

    def _call_llm(self, content, filename, user_cats, max_suggestions, user_id):
        """Single LLM call returning structured JSON."""
        cats_text = "\n".join(f"- {c}" for c in user_cats[:50]) if user_cats else "(none)"

        prompt = f"""You are a document categorizer.

User's categories:
{cats_text}

Filename: {filename}
Content: {content[:1500]}

Suggest {max_suggestions} categories.
Prefer existing ones.
Respond with JSON:
{{"categories": ["Cat1"], "confidence": 0.85}}"""

        response = self.client.chat.completions.create(
            model=self.cfg.llm_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=self.cfg.llm_temperature,
            timeout=self.cfg.llm_timeout,
        )

        try:
            data = json.loads(response.choices[0].message.content)
        except:
            return None

        if not data.get("categories"):
            return None

        return CategoryResult(
            categories=data["categories"][:max_suggestions],
            confidence=float(data.get("confidence", 0.5)),
            reasoning=data.get("reasoning", ""),
            source="llm",
            user_id=user_id,
        )


# ---------------------------------------------------------------------------
# Keyword Layer
# ---------------------------------------------------------------------------

class KeywordLayer(Layer):
    PATTERNS = {
        "invoice": "Invoices",
        "receipt": "Receipts",
        "tax": "Tax Documents",
        "syllabus": "Course Materials",
        "lecture": "Course Materials",
        "resume": "Resumes",
        "contract": "Contracts",
        "report": "Reports",
        "meeting": "Meeting Notes",
        "photo": "Photos",
        "medical": "Medical Records",
    }

    def __init__(self, config: CategorizationConfig):
        self.cfg = config

    def categorize(self, content, filename, user_cats, max_suggestions, user_id):
        """Simple deterministic keyword matching."""
        if not self.cfg.enable_keywords:
            return None

        text = (filename + " " + content[:500]).lower()
        matches = []

        for keyword, category in self.PATTERNS.items():
            if keyword in text and category not in matches:
                matches.append(category)
                if len(matches) >= max_suggestions:
                    break

        if matches:
            return CategoryResult(
                categories=matches,
                confidence=0.6,
                source="keyword",
                reasoning="Keyword match",
                user_id=user_id,
            )

        return None


# ---------------------------------------------------------------------------
# Default Layer
# ---------------------------------------------------------------------------

class DefaultLayer(Layer):
    def __init__(self, config: CategorizationConfig):
        self.cfg = config

    def categorize(self, content, filename, user_cats, max_suggestions, user_id):
        """Guaranteed fallback."""
        return CategoryResult(
            categories=[self.cfg.default_category],
            confidence=0.3,
            source="default",
            reasoning="Fallback",
            user_id=user_id,
        )


# ---------------------------------------------------------------------------
# Categorization Agent
# ---------------------------------------------------------------------------

class CategorizationAgent:
    def __init__(self, config: Optional[CategorizationConfig] = None, db_service=None):
        self.cfg = config or CategorizationConfig()
        self.db = db_service

        self.layers = [
            LLMLayer(self.cfg),
            KeywordLayer(self.cfg),
            DefaultLayer(self.cfg),
        ]

        self.metrics = {"total": 0, "llm": 0, "keyword": 0, "default": 0}

    def suggest(self, user_id, filename, content, max_suggestions=None):
        """Public API to categorize a document."""
        start = time.time()
        self.metrics["total"] += 1

        try:
            user_id, filename, content = self._validate(user_id, filename, content)
            max_suggestions = max_suggestions or self.cfg.max_suggestions
            user_cats = self._get_user_categories(user_id)

            for layer in self.layers:
                result = layer.categorize(content, filename, user_cats, max_suggestions, user_id)
                if result:
                    self.metrics[result.source] += 1
                    result.time_ms = (time.time() - start) * 1000
                    return result

            raise Exception("All layers unexpectedly failed")

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Categorization error: {e}")
            return CategoryResult(
                categories=[self.cfg.default_category],
                confidence=0.1,
                source="error",
                reasoning=str(e),
                user_id=user_id,
                time_ms=(time.time() - start) * 1000,
            )

    def _validate(self, user_id, filename, content):
        """Validate / sanitize inputs."""
        if not user_id or not isinstance(user_id, str):
            raise ValidationError("Invalid user_id")

        if not filename or not isinstance(filename, str):
            raise ValidationError("Invalid filename")

        if not content or not isinstance(content, str) or len(content) < 10:
            raise ValidationError("Invalid content")

        filename = filename[:255]
        content = content[: self.cfg.max_content_length]

        return user_id.strip(), filename.strip(), content.strip()

    def _get_user_categories(self, user_id):
        """Load per-user categories if DB available."""
        if not self.db:
            return []
        try:
            cats = self.db.get_categories_by_user(user_id)
            return [c["label"] for c in cats] if cats else []
        except:
            return []

    def get_metrics(self):
        """Return runtime metrics."""
        m = dict(self.metrics)
        if m["total"] > 0:
            m["llm_rate"] = m["llm"] / m["total"]
            m["keyword_rate"] = m["keyword"] / m["total"]
            m["default_rate"] = m["default"] / m["total"]
        return m
