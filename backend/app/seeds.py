"""
Seed default Buckets and PromptTemplates on first startup.
Idempotent - does not overwrite existing data.
"""
import uuid
from .database import SessionLocal
from .models.bucket import Bucket
from .models.prompt_template import PromptTemplate


DEFAULT_BUCKETS = [
    {
        "name": "Business",
        "description": "Construction, renovation, work sites, tools, project documentation, invoices",
        "priority": 10,
        "classification_prompt": (
            "Business includes construction, handyman, renovation sites, tools, materials, "
            "estimates, invoices, work progress, finished work, and project documentation."
        ),
    },
    {
        "name": "Documents",
        "description": "Receipts, invoices, contracts, scans, screenshots, notes, paper",
        "priority": 5,
        "classification_prompt": (
            "Documents include receipts, invoices, forms, scans, contracts, screenshots of "
            "emails, notes, whiteboards, and photos of paper. Documents beat Business when "
            "the asset is clearly a receipt, invoice, contract, scan, or photo of paper."
        ),
    },
    {
        "name": "Personal",
        "description": "Family, social events, travel, everyday life",
        "priority": 20,
        "classification_prompt": (
            "Personal includes family photos, selfies, social events, travel, food, pets, "
            "hobbies, and everyday life moments."
        ),
    },
    {
        "name": "Trash",
        "description": "Blurry, accidental, duplicates, test shots, no value",
        "priority": 100,
        "classification_prompt": (
            "Trash includes blurry photos, accidental shots, duplicates, test shots, "
            "completely dark or overexposed images with no value. "
            "When in doubt, do NOT classify as Trash — prefer another bucket."
        ),
    },
]

DEFAULT_PROMPTS = [
    {
        "prompt_type": "global_classification",
        "name": "Global Classification",
        "content": (
            "Classify this asset into the most appropriate Bucket using both image content "
            "and metadata. Be conservative when uncertain."
        ),
    },
    {
        "prompt_type": "description_generation",
        "name": "Description Generation",
        "content": (
            "Generate a concise, useful description that improves future search and review."
        ),
    },
    {
        "prompt_type": "tags_generation",
        "name": "Tags Generation",
        "content": (
            "Generate 3 to 8 practical, search-friendly tags. "
            "Prefer concrete terms over vague words."
        ),
    },
    {
        "prompt_type": "review_guidance",
        "name": "Review Guidance",
        "content": (
            "When reviewing AI suggestions, consider whether the bucket assignment matches "
            "the visible content. Override if the confidence is low or the explanation "
            "does not match what you see."
        ),
    },
]


def seed_defaults():
    db = SessionLocal()
    try:
        _seed_buckets(db)
        _seed_prompts(db)
    finally:
        db.close()


def _seed_buckets(db):
    for b in DEFAULT_BUCKETS:
        existing = db.query(Bucket).filter(Bucket.name == b["name"]).first()
        if not existing:
            db.add(Bucket(
                id=str(uuid.uuid4()),
                name=b["name"],
                description=b["description"],
                enabled=True,
                priority=b["priority"],
                mapping_mode="virtual",
                classification_prompt=b["classification_prompt"],
            ))
    db.commit()


def _seed_prompts(db):
    for p in DEFAULT_PROMPTS:
        existing = db.query(PromptTemplate).filter(
            PromptTemplate.prompt_type == p["prompt_type"],
            PromptTemplate.name == p["name"],
        ).first()
        if not existing:
            db.add(PromptTemplate(
                id=str(uuid.uuid4()),
                prompt_type=p["prompt_type"],
                name=p["name"],
                content=p["content"],
                enabled=True,
                version=1,
            ))
    db.commit()
