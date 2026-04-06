"""
PromptAssemblyService: combines global + bucket + field prompts into provider messages.
Prompts are first-class product objects, loaded from DB.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..models.prompt_template import PromptTemplate
from ..models.bucket import Bucket
from ..services.settings_utils import get_behaviour_setting


DEFAULT_GLOBAL_CLASSIFICATION = (
    "Classify this asset into the most appropriate Bucket using both image content "
    "and metadata. Be conservative when uncertain."
)
DEFAULT_DESCRIPTION_PROMPT = (
    "Generate a concise, useful description that improves future search and review."
)
DEFAULT_TAGS_PROMPT = (
    "Generate 3 to 8 practical, search-friendly tags. "
    "Prefer concrete terms over vague words."
)

DEFAULT_BUCKET_PROMPTS = {
    "Business": (
        "Business includes construction, handyman, renovation sites, tools, materials, "
        "estimates, invoices, work progress, finished work, and project documentation."
    ),
    "Documents": (
        "Documents include receipts, invoices, forms, scans, contracts, screenshots of "
        "emails, notes, whiteboards, and photos of paper. Documents beat Business when "
        "the asset is clearly a receipt, invoice, contract, scan, or photo of paper."
    ),
    "Personal": (
        "Personal includes family photos, selfies, social events, travel, food, pets, "
        "hobbies, and everyday life moments."
    ),
    "Trash": (
        "Trash includes blurry photos, accidental shots, duplicates, test shots, "
        "completely dark or overexposed images with no value. "
        "When in doubt, do NOT classify as Trash — prefer another bucket."
    ),
}


class PromptAssemblyService:
    def __init__(self, db: Session, user_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id

    def _get_behaviour_setting(self, key: str, default: bool) -> bool:
        return get_behaviour_setting(self.db, key, default, user_id=self.user_id)

    def _get_prompt(self, prompt_type: str, bucket_id: Optional[str] = None) -> Optional[str]:
        q = self.db.query(PromptTemplate).filter(
            PromptTemplate.prompt_type == prompt_type,
            PromptTemplate.enabled == True,
        )
        if self.user_id:
            q = q.filter(PromptTemplate.user_id == self.user_id)
        if bucket_id:
            q = q.filter(PromptTemplate.bucket_id == bucket_id)
        template = q.order_by(PromptTemplate.version.desc()).first()
        return template.content if template else None

    def assemble_classification_messages(
        self,
        asset_metadata: Dict[str, Any],
        buckets: List[Bucket],
        available_tags: Optional[List[str]] = None,
        available_albums: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build the message list for one-call AI classification.
        Returns provider-ready messages (without image - image injected by provider).

        available_tags: when set and allow_new_tags=False, used as the authoritative tag list.
        available_albums: when set and allow_new_albums=False, listed in the album constraint.
        """
        allow_new_tags = self._get_behaviour_setting("allow_new_tags", True)
        allow_new_albums = self._get_behaviour_setting("allow_new_albums", True)

        global_prompt = (
            self._get_prompt("global_classification")
            or DEFAULT_GLOBAL_CLASSIFICATION
        )
        description_prompt = (
            self._get_prompt("description_generation")
            or DEFAULT_DESCRIPTION_PROMPT
        )

        if allow_new_tags:
            tags_prompt = (
                self._get_prompt("tags_generation")
                or DEFAULT_TAGS_PROMPT
            )
        else:
            # Prefer the full Immich tag list if provided; fall back to asset's own tags.
            existing_tags = available_tags if available_tags is not None else (asset_metadata.get("tags") or [])
            if existing_tags:
                existing_str = ", ".join(existing_tags)
                tags_prompt = (
                    f"IMPORTANT: You must only use tags from the following existing tag list. "
                    f"Do NOT invent new tags. Available tags: {existing_str}. "
                    f"Select 0–8 relevant tags from that list only."
                )
            else:
                tags_prompt = (
                    "IMPORTANT: You must only use existing tags. No existing tags are available for this asset, "
                    "so return an empty tags array []."
                )

        if allow_new_albums:
            subalbum_note = ""
        else:
            if available_albums:
                albums_str = ", ".join(available_albums[:50])
                subalbum_note = (
                    f"\n\nIMPORTANT: For subalbum_suggestion, you may only use names from this existing album list: "
                    f"{albums_str}. Do NOT invent new album names. If no suitable album exists, "
                    "set subalbum_suggestion to null."
                )
            else:
                subalbum_note = (
                    "\n\nIMPORTANT: For subalbum_suggestion, you may only use names of albums that already exist "
                    "in Immich. Do NOT invent new album or sub-album names. If no suitable existing album exists, "
                    "set subalbum_suggestion to null."
                )

        bucket_defs = self._build_bucket_definitions(buckets)
        metadata_summary = self._build_metadata_summary(asset_metadata)
        output_schema = self._build_output_schema_instructions(buckets, allow_new_tags) + subalbum_note

        system_content = (
            f"You are an expert photo and document classifier and metadata enricher.\n\n"
            f"## Your Primary Task\n{global_prompt}\n\n"
            f"## Available Buckets\n{bucket_defs}\n\n"
            f"## Description Task\n{description_prompt}\n\n"
            f"## Tags Task\n{tags_prompt}\n\n"
            f"## Output Requirements\n{output_schema}"
        )

        user_content = (
            f"Please classify and enrich this asset.\n\n"
            f"## Asset Metadata\n{metadata_summary}\n\n"
            f"The asset image is attached. Analyze both the image and metadata together."
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _build_bucket_definitions(self, buckets: List[Bucket]) -> str:
        lines = []
        for b in sorted(buckets, key=lambda x: x.priority):
            if not b.enabled:
                continue
            bucket_prompt = (
                self._get_prompt("bucket_classification", bucket_id=b.id)
                or b.classification_prompt
                or DEFAULT_BUCKET_PROMPTS.get(b.name, "")
            )
            line = f"### {b.name}\n{bucket_prompt}"
            if b.examples_json:
                examples = ", ".join(b.examples_json[:5])
                line += f"\nExamples: {examples}"
            if b.negative_examples_json:
                neg = ", ".join(b.negative_examples_json[:5])
                line += f"\nNOT this bucket: {neg}"
            if b.confidence_threshold:
                line += f"\nMinimum confidence: {b.confidence_threshold}"
            lines.append(line)
        return "\n\n".join(lines)

    def _build_metadata_summary(self, metadata: Dict[str, Any]) -> str:
        parts = []
        if metadata.get("original_filename"):
            parts.append(f"Filename: {metadata['original_filename']}")
        if metadata.get("file_created_at"):
            parts.append(f"Date: {metadata['file_created_at']}")
        if metadata.get("asset_type"):
            parts.append(f"Type: {metadata['asset_type']}")
        if metadata.get("mime_type"):
            parts.append(f"MIME: {metadata['mime_type']}")
        if metadata.get("city") or metadata.get("country"):
            loc = ", ".join(filter(None, [metadata.get("city"), metadata.get("country")]))
            parts.append(f"Location: {loc}")
        if metadata.get("camera_make") or metadata.get("camera_model"):
            cam = " ".join(filter(None, [metadata.get("camera_make"), metadata.get("camera_model")]))
            parts.append(f"Camera: {cam}")
        if metadata.get("description"):
            parts.append(f"Current description: {metadata['description']}")
        if metadata.get("tags"):
            parts.append(f"Current tags: {', '.join(metadata['tags'])}")
        return "\n".join(parts) if parts else "No metadata available."

    def _build_output_schema_instructions(self, buckets: List[Bucket], allow_new_tags: bool = True) -> str:
        bucket_names = [b.name for b in buckets if b.enabled]
        names_str = ", ".join(f'"{n}"' for n in bucket_names)
        tags_desc = (
            "array of 3-8 strings"
            if allow_new_tags
            else "array of 0-8 strings chosen strictly from the provided tag list (may be empty [])"
        )
        return (
            f"Return ONLY a JSON object with these exact fields:\n"
            f"- bucket_name: one of [{names_str}]\n"
            f"- confidence: float 0.0-1.0\n"
            f"- explanation: string, 1-3 sentences\n"
            f"- description_suggestion: string, concise and useful\n"
            f"- tags: {tags_desc}\n"
            f"- subalbum_suggestion: string or null\n"
            f"- review_recommended: boolean\n\n"
            f"No other fields. No markdown. Valid JSON only."
        )

    def get_assembled_prompt_record(
        self,
        asset_metadata: Dict[str, Any],
        buckets: List[Bucket],
        available_tags: Optional[List[str]] = None,
        available_albums: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return the assembled prompt as a dict for storage/audit."""
        messages = self.assemble_classification_messages(
            asset_metadata, buckets,
            available_tags=available_tags,
            available_albums=available_albums,
        )
        return {
            "messages": messages,
            "bucket_names": [b.name for b in buckets if b.enabled],
            "metadata_summary": self._build_metadata_summary(asset_metadata),
        }
