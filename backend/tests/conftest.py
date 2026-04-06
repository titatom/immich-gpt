import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import patch

# Import all models so they register with Base.metadata before create_all
import app.models.asset  # noqa
import app.models.bucket  # noqa
import app.models.prompt_template  # noqa
import app.models.prompt_run  # noqa
import app.models.suggested_classification  # noqa
import app.models.suggested_metadata  # noqa
import app.models.review_decision  # noqa
import app.models.job_run  # noqa
import app.models.audit_log  # noqa
import app.models.provider_config  # noqa
import app.models.app_setting  # noqa

from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()

    from app.models.bucket import Bucket
    from app.models.prompt_template import PromptTemplate

    buckets = [
        {"name": "Business", "priority": 10},
        {"name": "Documents", "priority": 5},
        {"name": "Personal", "priority": 20},
        {"name": "Trash", "priority": 100},
    ]
    for b in buckets:
        session.add(Bucket(
            id=str(uuid.uuid4()),
            name=b["name"],
            enabled=True,
            priority=b["priority"],
            mapping_mode="virtual",
        ))

    prompts = [
        ("global_classification", "Global Classification",
         "Classify this asset into the most appropriate Bucket."),
        ("description_generation", "Description Generation",
         "Generate a concise, useful description."),
        ("tags_generation", "Tags Generation",
         "Generate 3 to 8 practical tags."),
    ]
    for pt, name, content in prompts:
        session.add(PromptTemplate(
            id=str(uuid.uuid4()),
            prompt_type=pt,
            name=name,
            content=content,
            enabled=True,
            version=1,
        ))
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.main.init_db"), patch("app.main.seed_defaults"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()
