"""
RoutingTreeService: CRUD over the hierarchical bucket tree.

All routing-tree behavior is generic: there is no category-specific
logic anywhere in this module.
"""
from __future__ import annotations
import uuid
from typing import Optional, List, Dict, Any, Iterable

from sqlalchemy.orm import Session

from ..models.bucket import Bucket
from ..schemas.bucket import (
    RoutingNodeCreate, RoutingNodeUpdate, RoutingNodeOut,
    VALID_DESTINATION_TYPES, VALID_PRIVACY_ACTIONS, VALID_QUALITY_LEVELS,
)


PATH_SEPARATOR = "/"


class RoutingTreeError(ValueError):
    pass


class RoutingTreeService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_nodes(self) -> List[Bucket]:
        return (
            self.db.query(Bucket)
            .filter(Bucket.user_id == self.user_id)
            .order_by(Bucket.priority, Bucket.name)
            .all()
        )

    def get_node(self, node_id: str) -> Bucket:
        b = self._get_or_none(node_id)
        if not b:
            raise RoutingTreeError(f"Routing node {node_id} not found")
        return b

    def _get_or_none(self, node_id: str) -> Optional[Bucket]:
        return (
            self.db.query(Bucket)
            .filter(Bucket.id == node_id, Bucket.user_id == self.user_id)
            .first()
        )

    def get_by_path(self, path: str) -> Optional[Bucket]:
        return (
            self.db.query(Bucket)
            .filter(Bucket.user_id == self.user_id, Bucket.path == path)
            .first()
        )

    def get_enabled_leaves(self) -> List[Bucket]:
        nodes = self.list_nodes()
        result: List[Bucket] = []
        for n in nodes:
            if not n.enabled:
                continue
            if n.is_leaf is False:
                continue
            if not self._all_ancestors_enabled(n, nodes):
                continue
            result.append(n)
        return result

    def _all_ancestors_enabled(self, node: Bucket, nodes: List[Bucket]) -> bool:
        by_id = {n.id: n for n in nodes}
        cur = node
        while cur.parent_id:
            parent = by_id.get(cur.parent_id)
            if not parent:
                return True
            if not parent.enabled:
                return False
            cur = parent
        return True

    def build_tree(self) -> List[Dict[str, Any]]:
        """Return a nested representation of the routing tree."""
        nodes = self.list_nodes()
        outs: Dict[str, Dict[str, Any]] = {n.id: self.serialize(n) for n in nodes}
        for d in outs.values():
            d["children"] = []
        roots: List[Dict[str, Any]] = []
        for n in nodes:
            if n.parent_id and n.parent_id in outs:
                outs[n.parent_id]["children"].append(outs[n.id])
            else:
                roots.append(outs[n.id])
        return roots

    # ------------------------------------------------------------------
    # Mutate
    # ------------------------------------------------------------------

    def create_node(self, data: RoutingNodeCreate) -> Bucket:
        self._validate_destination_type(data.destination_type)
        self._validate_quality_level(data.minimum_quality)
        self._validate_privacy_rules(data.privacy_rules)
        self._validate_thresholds(data.auto_apply_threshold, data.review_below_threshold)

        parent: Optional[Bucket] = None
        if data.parent_id:
            parent = self._get_or_none(data.parent_id)
            if not parent:
                raise RoutingTreeError(f"Parent node {data.parent_id} not found")

        path = self._compute_path(data.name, parent)
        self._check_unique_path(path)

        node = Bucket(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            parent_id=parent.id if parent else None,
            name=data.name,
            path=path,
            is_leaf=data.is_leaf,
            description=data.description,
            enabled=data.enabled,
            priority=data.priority,
            mapping_mode=self._destination_to_mapping_mode(data.destination_type),
            destination_type=data.destination_type,
            immich_album_name=data.immich_album_name,
            create_album_if_missing=data.create_album_if_missing,
            auto_apply_enabled=data.auto_apply_enabled,
            auto_apply_threshold=data.auto_apply_threshold,
            review_below_threshold=data.review_below_threshold,
            exclusive=data.exclusive,
            allow_secondary=data.allow_secondary,
            minimum_quality=data.minimum_quality,
            allow_blurry=data.allow_blurry,
            allow_dark=data.allow_dark,
            allow_screenshot=data.allow_screenshot,
            allow_duplicate=data.allow_duplicate,
            suggest_description=data.suggest_description,
            suggest_tags=data.suggest_tags,
            suggest_location=data.suggest_location,
            suggest_caption=data.suggest_caption,
            write_description=data.write_description,
            write_tags=data.write_tags,
            write_location=data.write_location,
            custom_prompt_enabled=data.custom_prompt_enabled,
            custom_prompt=data.custom_prompt,
            positive_criteria_json=data.positive_criteria,
            negative_criteria_json=data.negative_criteria,
            privacy_rules_json=data.privacy_rules,
            quality_rules_json=data.quality_rules,
            automation_rules_json=data.automation_rules,
            metadata_rules_json=data.metadata_rules,
        )
        # If creating under a parent that is currently a leaf, demote it
        # to a parent (parents are organizational only).
        if parent and parent.is_leaf:
            parent.is_leaf = False

        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def update_node(self, node_id: str, data: RoutingNodeUpdate) -> Bucket:
        node = self.get_node(node_id)

        if data.destination_type is not None:
            self._validate_destination_type(data.destination_type)
            node.destination_type = data.destination_type
            node.mapping_mode = self._destination_to_mapping_mode(data.destination_type)

        if data.minimum_quality is not None:
            self._validate_quality_level(data.minimum_quality)
            node.minimum_quality = data.minimum_quality

        if data.privacy_rules is not None:
            self._validate_privacy_rules(data.privacy_rules)
            node.privacy_rules_json = data.privacy_rules

        if data.auto_apply_threshold is not None or data.review_below_threshold is not None:
            self._validate_thresholds(
                data.auto_apply_threshold if data.auto_apply_threshold is not None else node.auto_apply_threshold,
                data.review_below_threshold if data.review_below_threshold is not None else node.review_below_threshold,
            )

        if data.name is not None and data.name != node.name:
            self.rename_node(node, data.name, commit=False)

        scalar_fields = (
            "description", "enabled", "priority",
            "immich_album_name", "create_album_if_missing",
            "auto_apply_enabled", "auto_apply_threshold", "review_below_threshold",
            "exclusive", "allow_secondary",
            "allow_blurry", "allow_dark", "allow_screenshot", "allow_duplicate",
            "suggest_description", "suggest_tags", "suggest_location", "suggest_caption",
            "write_description", "write_tags", "write_location",
            "custom_prompt_enabled", "custom_prompt",
            "is_leaf",
        )
        for field in scalar_fields:
            value = getattr(data, field)
            if value is not None:
                setattr(node, field, value)

        if data.positive_criteria is not None:
            node.positive_criteria_json = data.positive_criteria
        if data.negative_criteria is not None:
            node.negative_criteria_json = data.negative_criteria
        if data.quality_rules is not None:
            node.quality_rules_json = data.quality_rules
        if data.automation_rules is not None:
            node.automation_rules_json = data.automation_rules
        if data.metadata_rules is not None:
            node.metadata_rules_json = data.metadata_rules

        self.db.commit()
        self.db.refresh(node)
        return node

    def rename_node(self, node: Bucket, new_name: str, commit: bool = True) -> Bucket:
        if not new_name or not new_name.strip():
            raise RoutingTreeError("Node name cannot be empty")
        new_name = new_name.strip()
        if PATH_SEPARATOR in new_name:
            raise RoutingTreeError(
                f"Node name must not contain '{PATH_SEPARATOR}'"
            )
        parent = self._get_or_none(node.parent_id) if node.parent_id else None
        new_path = self._compute_path(new_name, parent)
        if new_path != node.path:
            self._check_unique_path(new_path, ignore_id=node.id)
        old_path = node.path or node.name
        node.name = new_name
        node.path = new_path
        # Update descendants' paths
        self._rewrite_descendant_paths(old_prefix=old_path, new_prefix=new_path)
        if commit:
            self.db.commit()
            self.db.refresh(node)
        return node

    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> Bucket:
        node = self.get_node(node_id)
        if new_parent_id == node_id:
            raise RoutingTreeError("Cannot move a node into itself")

        new_parent: Optional[Bucket] = None
        if new_parent_id:
            new_parent = self._get_or_none(new_parent_id)
            if not new_parent:
                raise RoutingTreeError(f"Target parent {new_parent_id} not found")
            if self._is_descendant(new_parent, node):
                raise RoutingTreeError("Cannot move a node into one of its descendants")

        old_path = node.path or node.name
        node.parent_id = new_parent.id if new_parent else None
        node.path = self._compute_path(node.name, new_parent)
        self._check_unique_path(node.path, ignore_id=node.id)
        self._rewrite_descendant_paths(old_prefix=old_path, new_prefix=node.path)

        if new_parent and new_parent.is_leaf:
            new_parent.is_leaf = False

        self.db.commit()
        self.db.refresh(node)
        return node

    def delete_node(self, node_id: str, cascade: bool = False) -> None:
        node = self.get_node(node_id)
        children = (
            self.db.query(Bucket)
            .filter(Bucket.parent_id == node.id, Bucket.user_id == self.user_id)
            .all()
        )
        if children and not cascade:
            raise RoutingTreeError(
                "Cannot delete a node with children unless cascade=true"
            )
        if cascade:
            for child in children:
                self.delete_node(child.id, cascade=True)
        self.db.delete(node)
        self.db.commit()

    def duplicate_node(self, node_id: str) -> Bucket:
        node = self.get_node(node_id)
        copy_name = f"{node.name} (copy)"
        # ensure unique sibling name
        suffix = 1
        parent = self._get_or_none(node.parent_id) if node.parent_id else None
        while True:
            candidate_path = self._compute_path(copy_name, parent)
            if not self.get_by_path(candidate_path):
                break
            suffix += 1
            copy_name = f"{node.name} (copy {suffix})"

        new_node = Bucket(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            parent_id=node.parent_id,
            name=copy_name,
            path=self._compute_path(copy_name, parent),
            is_leaf=node.is_leaf,
            description=node.description,
            enabled=node.enabled,
            priority=node.priority,
            mapping_mode=node.mapping_mode,
            destination_type=node.destination_type,
            immich_album_name=node.immich_album_name,
            create_album_if_missing=node.create_album_if_missing,
            auto_apply_enabled=node.auto_apply_enabled,
            auto_apply_threshold=node.auto_apply_threshold,
            review_below_threshold=node.review_below_threshold,
            exclusive=node.exclusive,
            allow_secondary=node.allow_secondary,
            minimum_quality=node.minimum_quality,
            allow_blurry=node.allow_blurry,
            allow_dark=node.allow_dark,
            allow_screenshot=node.allow_screenshot,
            allow_duplicate=node.allow_duplicate,
            suggest_description=node.suggest_description,
            suggest_tags=node.suggest_tags,
            suggest_location=node.suggest_location,
            suggest_caption=node.suggest_caption,
            write_description=node.write_description,
            write_tags=node.write_tags,
            write_location=node.write_location,
            custom_prompt_enabled=node.custom_prompt_enabled,
            custom_prompt=node.custom_prompt,
            positive_criteria_json=list(node.positive_criteria_json or []),
            negative_criteria_json=list(node.negative_criteria_json or []),
            privacy_rules_json=dict(node.privacy_rules_json or {}),
            quality_rules_json=dict(node.quality_rules_json or {}),
            automation_rules_json=dict(node.automation_rules_json or {}),
            metadata_rules_json=dict(node.metadata_rules_json or {}),
        )
        self.db.add(new_node)
        self.db.commit()
        self.db.refresh(new_node)
        return new_node

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def serialize(self, node: Bucket) -> Dict[str, Any]:
        return {
            "id": node.id,
            "parent_id": node.parent_id,
            "name": node.name,
            "path": node.path or node.name,
            "is_leaf": bool(node.is_leaf) if node.is_leaf is not None else True,
            "description": node.description,
            "enabled": bool(node.enabled),
            "priority": node.priority or 100,
            "destination_type": node.destination_type or "virtual",
            "immich_album_name": node.immich_album_name,
            "create_album_if_missing": bool(
                node.create_album_if_missing if node.create_album_if_missing is not None else True
            ),
            "auto_apply_enabled": bool(node.auto_apply_enabled),
            "auto_apply_threshold": float(
                node.auto_apply_threshold if node.auto_apply_threshold is not None else 0.95
            ),
            "review_below_threshold": (
                float(node.review_below_threshold)
                if node.review_below_threshold is not None
                else None
            ),
            "exclusive": bool(node.exclusive),
            "allow_secondary": bool(
                node.allow_secondary if node.allow_secondary is not None else True
            ),
            "minimum_quality": node.minimum_quality or "any",
            "allow_blurry": bool(node.allow_blurry if node.allow_blurry is not None else True),
            "allow_dark": bool(node.allow_dark if node.allow_dark is not None else True),
            "allow_screenshot": bool(
                node.allow_screenshot if node.allow_screenshot is not None else True
            ),
            "allow_duplicate": bool(
                node.allow_duplicate if node.allow_duplicate is not None else True
            ),
            "suggest_description": bool(
                node.suggest_description if node.suggest_description is not None else True
            ),
            "suggest_tags": bool(node.suggest_tags if node.suggest_tags is not None else True),
            "suggest_location": bool(
                node.suggest_location if node.suggest_location is not None else False
            ),
            "suggest_caption": bool(
                node.suggest_caption if node.suggest_caption is not None else False
            ),
            "write_description": bool(
                node.write_description if node.write_description is not None else True
            ),
            "write_tags": bool(node.write_tags if node.write_tags is not None else True),
            "write_location": bool(
                node.write_location if node.write_location is not None else False
            ),
            "custom_prompt_enabled": bool(node.custom_prompt_enabled),
            "custom_prompt": node.custom_prompt,
            "positive_criteria": list(node.positive_criteria_json or []),
            "negative_criteria": list(node.negative_criteria_json or []),
            "privacy_rules": dict(node.privacy_rules_json or {}),
            "quality_rules": dict(node.quality_rules_json or {}),
            "automation_rules": dict(node.automation_rules_json or {}),
            "metadata_rules": dict(node.metadata_rules_json or {}),
            "created_at": node.created_at,
            "updated_at": node.updated_at,
            "children": [],
        }

    def _compute_path(self, name: str, parent: Optional[Bucket]) -> str:
        if parent and parent.path:
            return f"{parent.path}{PATH_SEPARATOR}{name}"
        return name

    def _check_unique_path(self, path: str, ignore_id: Optional[str] = None) -> None:
        q = self.db.query(Bucket).filter(
            Bucket.user_id == self.user_id,
            Bucket.path == path,
        )
        if ignore_id:
            q = q.filter(Bucket.id != ignore_id)
        if q.first():
            raise RoutingTreeError(f"Routing path '{path}' already exists")

    def _rewrite_descendant_paths(self, old_prefix: str, new_prefix: str) -> None:
        if old_prefix == new_prefix:
            return
        descendants = (
            self.db.query(Bucket)
            .filter(
                Bucket.user_id == self.user_id,
                Bucket.path.like(f"{old_prefix}{PATH_SEPARATOR}%"),
            )
            .all()
        )
        for d in descendants:
            if d.path:
                d.path = new_prefix + d.path[len(old_prefix):]

    def _is_descendant(self, candidate: Bucket, ancestor: Bucket) -> bool:
        cur: Optional[Bucket] = candidate
        while cur is not None:
            if cur.id == ancestor.id:
                return True
            if not cur.parent_id:
                return False
            cur = self._get_or_none(cur.parent_id)
        return False

    @staticmethod
    def _validate_destination_type(value: str) -> None:
        if value not in VALID_DESTINATION_TYPES:
            raise RoutingTreeError(
                f"Invalid destination_type '{value}'. "
                f"Must be one of: {sorted(VALID_DESTINATION_TYPES)}"
            )

    @staticmethod
    def _validate_quality_level(value: str) -> None:
        if value not in VALID_QUALITY_LEVELS:
            raise RoutingTreeError(
                f"Invalid minimum_quality '{value}'. "
                f"Must be one of: {sorted(VALID_QUALITY_LEVELS)}"
            )

    @staticmethod
    def _validate_privacy_rules(rules: Optional[Dict[str, str]]) -> None:
        if not rules:
            return
        for k, v in rules.items():
            if v not in VALID_PRIVACY_ACTIONS:
                raise RoutingTreeError(
                    f"Privacy rule '{k}'='{v}' invalid. "
                    f"Must be one of: {sorted(VALID_PRIVACY_ACTIONS)}"
                )

    @staticmethod
    def _validate_thresholds(auto: Optional[float], review: Optional[float]) -> None:
        for label, val in (("auto_apply_threshold", auto), ("review_below_threshold", review)):
            if val is None:
                continue
            if not (0.0 <= float(val) <= 1.0):
                raise RoutingTreeError(f"{label} must be between 0.0 and 1.0")

    @staticmethod
    def _destination_to_mapping_mode(destination_type: str) -> str:
        return {
            "virtual": "virtual",
            "immich_album": "immich_album",
            "immich_trash": "immich_trash",
            "review_only": "review_only",
        }.get(destination_type, "virtual")
