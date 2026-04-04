"""Specialized debugger for categorization workflow."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from types import SimpleNamespace

from colorama import Fore, Back, Style, init

from settings import get_settings

# Initialize color handling once
init(autoreset=True)


class CategorizationDebugger:
    """Handles verbose, structured logging for categorization when enabled."""

    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = settings.debug_categorization
        self.output_format = settings.debug_output_format.lower()
        self.log_file = settings.debug_log_file

        self.colors_enabled = self.output_format == "colored"
        if self.colors_enabled:
            self._fore = Fore
            self._back = Back
            self._style = Style
        else:
            self._fore = SimpleNamespace(
                CYAN='',
                YELLOW='',
                WHITE='',
                GREEN='',
                RED='',
                BLACK=''
            )
            self._back = SimpleNamespace(
                BLUE='',
                CYAN=''
            )
            self._style = SimpleNamespace(RESET_ALL='')

        self.start_time: Optional[float] = None
        self.steps: List[Dict[str, Any]] = []
        self.filename: str = ""
        self.document_id: str = ""
        self._max_rows = 5

    # ------------------------------------------------------------------ #
    # Lifecycle helpers
    # ------------------------------------------------------------------ #
    def start_categorization(self, document_id: str, filename: str) -> None:
        if not self.enabled:
            return

        self.document_id = document_id
        self.filename = filename
        self.start_time = time.time()
        self.steps = []

        if self.output_format == "json":
            self._print_json_header()
            return

        self._print_header(f"CATEGORIZATION DEBUG: {filename}")
        self._print_info("Document ID", document_id)
        self._print_info("Timestamp", datetime.utcnow().isoformat())
        self._print_divider()

    def end_categorization(self) -> None:
        if not self.enabled:
            return

        if self.start_time:
            elapsed = time.time() - self.start_time
        else:
            elapsed = 0.0

        if self.output_format == "json":
            self._print_json_footer(elapsed)
        else:
            self._print_section("PERFORMANCE")
            self._print_info("Total Time", f"{elapsed:.3f}s")
            self._print_info("Steps Logged", len(self.steps))
            self._print_footer()

        if self.log_file:
            self._write_to_file(elapsed)

        # Reset state
        self.start_time = None
        self.steps = []
        self.filename = ""
        self.document_id = ""

    # ------------------------------------------------------------------ #
    # Logging helpers (no-ops when disabled)
    # ------------------------------------------------------------------ #
    def log_embedding_info(
        self,
        embedding_dim: int,
        embedding_norm: float,
        num_chunks: int,
        sample: Optional[List[float]] = None,
    ) -> None:
        if not self.enabled:
            return

        data = {
            "embedding_dim": embedding_dim,
            "embedding_norm": round(embedding_norm, 4),
            "num_chunks": num_chunks,
        }
        if sample:
            data["embedding_sample"] = [round(v, 4) for v in sample[:10]]

        self._add_step("embedding", data)

        if self.output_format == "json":
            return

        self._print_section("EMBEDDING")
        summary = (
            f"dim={embedding_dim}, norm={embedding_norm:.4f}, "
            f"chunks={num_chunks}"
        )
        if sample:
            summary += f", sample={data['embedding_sample'][:5]}"
        self._print_info("Summary", summary)

    def log_keyword_analysis(
        self,
        suggested_categories: List[str],
        keyword_scores: Dict[str, int],
        filename: str,
        content_preview: str,
    ) -> None:
        if not self.enabled:
            return

        data = {
            "suggested_categories": suggested_categories,
            "keyword_scores": keyword_scores,
            "filename": filename,
            "content_preview": content_preview[:500],
        }
        self._add_step("keywords", data)

        if self.output_format == "json":
            return

        self._print_section("KEYWORDS")
        compact_preview = content_preview[:180].replace("\n", " ")
        if len(content_preview) > 180:
            compact_preview += "..."
        self._print_info("Filename", filename)
        self._print_info("Preview", compact_preview)

        if suggested_categories:
            suggestions = ", ".join(
                f"{cat}({keyword_scores.get(cat, 0)})" for cat in suggested_categories
            )
            self._print_info("Suggestions", suggestions)

    def log_similarity_matrix(
        self,
        similarities: List[Dict[str, Any]],
        threshold: float,
        dynamic_threshold: float,
    ) -> None:
        if not self.enabled:
            return

        data = {
            "threshold": round(threshold, 3),
            "dynamic_threshold": round(dynamic_threshold, 3),
            "similarities": [
                {
                    "category": entry['category']['label'],
                    "raw_similarity": round(entry['similarity'], 4),
                    "boosted_similarity": round(entry.get('boosted_similarity', entry['similarity']), 4),
                    "keyword_match": entry.get('keyword_match', False),
                    "is_initialized": entry.get('is_initialized', True),
                }
                for entry in similarities
            ][: self._max_rows],
        }
        self._add_step("similarities", data)

        if self.output_format == "json":
            return

        self._print_section("SEMANTIC SIMILARITY")
        self._print_info("Base Threshold", data["threshold"])
        self._print_info("Dynamic Threshold", data["dynamic_threshold"])

        print(f"\n{self._fore.CYAN}Category Similarities:{self._style.RESET_ALL}")
        print(f"{'Category':30} {'Raw':>8} {'Boosted':>10} {'Keyword':>9} {'Status':>10}")
        print("-" * 75)

        for entry in data["similarities"][: self._max_rows]:
            raw = entry["raw_similarity"]
            boosted = entry["boosted_similarity"]
            keyword = "✓" if entry["keyword_match"] else "✗"
            is_initialized = entry["is_initialized"]

            status = "MATCH" if boosted >= dynamic_threshold else "LOW"
            if boosted >= threshold and boosted < dynamic_threshold:
                status = "CLOSE"
            if not is_initialized:
                status += " (uninit)"

            color = (
                self._fore.GREEN
                if status.startswith("MATCH")
                else self._fore.YELLOW
                if status.startswith("CLOSE")
                else self._fore.WHITE
            )
            print(
                f"{color}{entry['category']:30}{self._style.RESET_ALL} "
                f"{raw:>8.4f} {boosted:>10.4f} {keyword:>9} {status:>10}"
            )

    def log_decision(self, decision: str, reason: str, category: Optional[str], similarity: float) -> None:
        if not self.enabled:
            return

        data = {
            "decision": decision,
            "reason": reason,
            "category": category,
            "similarity": round(similarity, 4),
        }
        self._add_step("decision", data)

        if self.output_format == "json":
            return

        self._print_section("DECISION")
        self._print_info("Decision", decision.upper())
        self._print_info("Category", category or "None")
        self._print_info("Similarity", f"{similarity:.4f}")
        self._print_info("Reason", reason)

    def log_final_result(self, result: Dict[str, Any]) -> None:
        if not self.enabled:
            return

        self._add_step("result", result)

        if self.output_format == "json":
            return

        self._print_section("RESULT")
        for key, value in result.items():
            self._print_info(key.replace("_", " ").title(), value)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _print_header(self, title: str) -> None:
        print("\n" + "=" * 80)
        print(f"{self._back.BLUE}{self._fore.WHITE} {title} {self._style.RESET_ALL}")
        print("=" * 80)

    def _print_footer(self) -> None:
        print("=" * 80 + "\n")

    def _print_section(self, title: str) -> None:
        print(f"\n{self._back.CYAN}{self._fore.BLACK} {title} {self._style.RESET_ALL}")
        print("-" * 80)

    def _print_info(self, label: str, value: Any) -> None:
        print(f"{self._fore.CYAN}{label}:{self._style.RESET_ALL} {value}")

    def _print_list_item(self, text: str, level: int = 0) -> None:
        indent = "  " * level
        print(f"{indent}{self._fore.YELLOW}•{self._style.RESET_ALL} {text}")

    def _print_divider(self) -> None:
        print("-" * 80)

    def _print_json_header(self) -> None:
        print(json.dumps({
            "document_id": self.document_id,
            "filename": self.filename,
            "timestamp": datetime.utcnow().isoformat(),
            "steps": [],
        }))

    def _print_json_footer(self, elapsed: float) -> None:
        payload = {
            "document_id": self.document_id,
            "filename": self.filename,
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_time": round(elapsed, 3),
            "steps": self.steps,
        }
        print(json.dumps(payload, indent=2))

    def _add_step(self, name: str, data: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        self.steps.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        })

    def _write_to_file(self, elapsed: float) -> None:
        if not self.log_file:
            return

        payload = {
            "document_id": self.document_id,
            "filename": self.filename,
            "elapsed_time": round(elapsed, 3),
            "steps": self.steps,
        }

        try:
            path = Path(self.log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a') as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as exc:
            print(f"{self._fore.RED}Failed to write debug log: {exc}{self._style.RESET_ALL}")


_debugger: Optional[CategorizationDebugger] = None


def get_categorization_debugger() -> CategorizationDebugger:
    global _debugger
    if _debugger is None:
        _debugger = CategorizationDebugger()
    return _debugger
