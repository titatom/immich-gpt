"""
RoutingDecisionService

The LLM may suggest paths and metadata; the backend enforces every rule
before any writeback or auto-apply.  All behavior here is generic and
driven entirely by leaf settings.
"""
from __future__ import annotations
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from ..models.bucket import Bucket
from .routing_schemas import (
    AIRoutingResult, AISecondaryPath, RuleResult, Candidate, RoutingDecision,
    AISafetyFlags, AIQualityFlags,
)


class RoutingDecisionService:
    def __init__(self, db: Session, user_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Rule evaluation for a single leaf
    # ------------------------------------------------------------------

    def evaluate_leaf_rules(
        self,
        leaf: Bucket,
        confidence: float,
        safety_flags: AISafetyFlags,
        quality_flags: AIQualityFlags,
    ) -> RuleResult:
        review_reasons: List[str] = []

        # Privacy rules
        privacy = leaf.privacy_rules_json or {}
        for flag, value in safety_flags.model_dump().items():
            action = privacy.get(flag, "allow")
            if not value:
                continue
            if action == "reject":
                return RuleResult(rejected=True, reason=f"{flag}_rejected")
            if action == "review":
                review_reasons.append(f"{flag}_requires_review")
            elif action == "tag":
                review_reasons.append(f"{flag}_tagged")
            # "allow" → no-op

        # Quality rules
        if not leaf.allow_blurry and quality_flags.blurry:
            return RuleResult(rejected=True, reason="blurry_rejected")
        if not leaf.allow_dark and quality_flags.dark:
            return RuleResult(rejected=True, reason="dark_rejected")
        if not leaf.allow_screenshot and quality_flags.screenshot:
            return RuleResult(rejected=True, reason="screenshot_rejected")
        if not leaf.allow_duplicate and quality_flags.duplicate_candidate:
            review_reasons.append("duplicate_requires_review")

        if quality_flags.low_quality and (leaf.minimum_quality or "any") == "high":
            return RuleResult(rejected=True, reason="quality_below_minimum")

        # Confidence threshold
        threshold = leaf.review_below_threshold
        if threshold is not None and confidence < threshold:
            review_reasons.append("low_confidence")

        return RuleResult(
            rejected=False,
            review_required=bool(review_reasons),
            review_reasons=review_reasons,
        )

    # ------------------------------------------------------------------
    # Top-level decision
    # ------------------------------------------------------------------

    def resolve_routing(
        self,
        ai_result: AIRoutingResult,
        leaves: List[Bucket],
    ) -> RoutingDecision:
        leaf_by_path: Dict[str, Bucket] = {l.path or l.name: l for l in leaves}

        suggestions: List[AISecondaryPath] = []
        if ai_result.primary_path and ai_result.primary_confidence is not None:
            suggestions.append(
                AISecondaryPath(
                    path=ai_result.primary_path,
                    confidence=float(ai_result.primary_confidence),
                )
            )
        for s in ai_result.secondary_paths:
            suggestions.append(s)

        candidates: List[Candidate] = []
        rejected_paths: List[Dict] = []

        for s in suggestions:
            leaf = leaf_by_path.get(s.path)
            if not leaf:
                rejected_paths.append({"path": s.path, "reason": "unknown_path"})
                continue
            if not leaf.enabled or not leaf.is_leaf:
                rejected_paths.append({"path": s.path, "reason": "leaf_disabled"})
                continue
            rule = self.evaluate_leaf_rules(
                leaf,
                confidence=float(s.confidence),
                safety_flags=ai_result.safety_flags,
                quality_flags=ai_result.quality_flags,
            )
            if rule.rejected:
                rejected_paths.append(
                    {"path": s.path, "reason": rule.reason or "rejected"}
                )
                continue
            candidates.append(
                Candidate(
                    bucket_id=leaf.id,
                    path=leaf.path or leaf.name,
                    confidence=float(s.confidence),
                    review_required=rule.review_required,
                    review_reasons=rule.review_reasons,
                    priority=int(leaf.priority or 100),
                    exclusive=bool(leaf.exclusive),
                    allow_secondary=bool(
                        leaf.allow_secondary if leaf.allow_secondary is not None else True
                    ),
                )
            )

        # Sort by (priority asc, confidence desc); lower priority number wins
        candidates.sort(key=lambda c: (c.priority, -c.confidence))

        primary: Optional[Candidate] = candidates[0] if candidates else None
        secondary: List[Candidate] = []
        if primary:
            if primary.exclusive or not primary.allow_secondary:
                secondary = []
            else:
                # Only keep secondary candidates that themselves allow being secondary
                secondary = [
                    c for c in candidates[1:]
                    if c.bucket_id != primary.bucket_id
                ]

        review_reasons: List[str] = list(ai_result.review_reasons)
        if primary:
            review_reasons.extend(primary.review_reasons)
        if ai_result.review_required:
            review_reasons.append("ai_requested_review")

        if not primary:
            review_reasons.append("no_matching_destination")

        # Disposition
        disposition = ai_result.disposition or "review"
        if primary:
            leaf = leaf_by_path.get(primary.path)
            if leaf and leaf.destination_type == "immich_trash":
                disposition = "trash_candidate"

        review_required = bool(review_reasons) or ai_result.review_required or not primary

        # Auto-apply
        auto_apply = self._can_auto_apply(
            primary, leaf_by_path, review_required
        )

        return RoutingDecision(
            primary=primary,
            secondary=secondary,
            disposition=disposition,
            review_required=review_required,
            auto_apply=auto_apply,
            review_reasons=list(dict.fromkeys(review_reasons)),
            reason_codes=list(ai_result.reason_codes),
            safety_flags=ai_result.safety_flags.model_dump(),
            quality_flags=ai_result.quality_flags.model_dump(),
            rejected_paths=rejected_paths,
        )

    def _can_auto_apply(
        self,
        primary: Optional[Candidate],
        leaf_by_path: Dict[str, Bucket],
        review_required: bool,
    ) -> bool:
        if review_required or not primary:
            return False
        leaf = leaf_by_path.get(primary.path)
        if not leaf:
            return False
        if not leaf.auto_apply_enabled:
            return False
        if primary.confidence < float(leaf.auto_apply_threshold or 0.95):
            return False
        # Trash never auto-applies unless explicitly enabled on the leaf.
        # (Behavior comes from the leaf setting only — no name-based logic.)
        if leaf.destination_type == "immich_trash" and not leaf.auto_apply_enabled:
            return False
        return True
