"""
LeafPromptCompiler: builds an AI-instruction block for a single routing leaf.
The compiled prompt is purely derived from leaf settings — no category-
specific logic.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models.bucket import Bucket
from ..models.routing_example import RoutingExample
from ..models.asset import Asset


class LeafPromptCompiler:
    def __init__(self, db: Session, user_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id

    def compile(self, leaf: Bucket) -> str:
        """Return the per-leaf AI instructions as a single text block."""
        lines: List[str] = []
        path = leaf.path or leaf.name
        lines.append(f"Destination path: {path}")

        if leaf.description:
            lines.append("")
            lines.append(f"Purpose: {leaf.description}")

        positive = leaf.positive_criteria_json or []
        if positive:
            lines.append("")
            lines.append("Select this destination when:")
            for item in positive:
                lines.append(f"  - {item}")

        negative = leaf.negative_criteria_json or []
        if negative:
            lines.append("")
            lines.append("Do not select this destination when:")
            for item in negative:
                lines.append(f"  - {item}")

        quality = self._format_quality_rules(leaf)
        if quality:
            lines.append("")
            lines.append("Quality rules:")
            for q in quality:
                lines.append(f"  - {q}")

        privacy = leaf.privacy_rules_json or {}
        if privacy:
            lines.append("")
            lines.append("Privacy rules (allow / tag / review / reject):")
            for k, v in privacy.items():
                lines.append(f"  - {k}: {v}")

        automation = self._format_automation_rules(leaf)
        if automation:
            lines.append("")
            lines.append("Automation:")
            for a in automation:
                lines.append(f"  - {a}")

        examples = self._fetch_examples(leaf)
        positive_ex = examples.get("positive", [])
        negative_ex = examples.get("negative", [])
        if positive_ex or negative_ex:
            lines.append("")
            lines.append("Examples:")
            if positive_ex:
                lines.append("  Positive:")
                for e in positive_ex:
                    lines.append(f"    - {e}")
            if negative_ex:
                lines.append("  Negative:")
                for e in negative_ex:
                    lines.append(f"    - {e}")

        if leaf.custom_prompt_enabled and leaf.custom_prompt:
            lines.append("")
            lines.append("Additional user instructions:")
            lines.append(leaf.custom_prompt.strip())

        if leaf.destination_type == "immich_trash":
            lines.append("")
            lines.append(
                "NOTE: This destination represents Immich trash. "
                "Set disposition='trash_candidate' when matching here."
            )

        return "\n".join(lines).strip()

    def compile_global(self, leaves: List[Bucket]) -> str:
        """Compile a context block listing every enabled leaf for the prompt."""
        sections: List[str] = []
        for leaf in leaves:
            if not leaf.enabled or not leaf.is_leaf:
                continue
            sections.append(self.compile(leaf))
            sections.append("")
        return "\n".join(sections).strip()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_quality_rules(self, leaf: Bucket) -> List[str]:
        items: List[str] = []
        mq = leaf.minimum_quality or "any"
        if mq != "any":
            items.append(f"Minimum acceptable quality: {mq}")
        if not leaf.allow_blurry:
            items.append("Reject blurry images")
        if not leaf.allow_dark:
            items.append("Reject dark / underexposed images")
        if not leaf.allow_screenshot:
            items.append("Reject screenshots")
        if not leaf.allow_duplicate:
            items.append("Mark duplicate candidates for review")
        return items

    def _format_automation_rules(self, leaf: Bucket) -> List[str]:
        items: List[str] = []
        if leaf.auto_apply_enabled:
            items.append(
                f"Auto-apply allowed at confidence >= {leaf.auto_apply_threshold}"
            )
        else:
            items.append("Auto-apply disabled — every match requires review")
        if leaf.review_below_threshold is not None:
            items.append(
                f"Force review below confidence {leaf.review_below_threshold}"
            )
        return items

    def _fetch_examples(self, leaf: Bucket) -> Dict[str, List[str]]:
        rows = (
            self.db.query(RoutingExample)
            .filter(RoutingExample.bucket_id == leaf.id)
            .order_by(RoutingExample.created_at.desc())
            .limit(20)
            .all()
        )
        if not rows:
            return {"positive": [], "negative": []}
        result = {"positive": [], "negative": []}
        for r in rows:
            label = r.note or self._asset_label(r.asset_id)
            if not label:
                continue
            if r.example_type == "negative":
                result["negative"].append(label)
            else:
                result["positive"].append(label)
        return result

    def _asset_label(self, asset_id: Optional[str]) -> Optional[str]:
        if not asset_id:
            return None
        a = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not a:
            return None
        return a.original_filename or a.immich_id
