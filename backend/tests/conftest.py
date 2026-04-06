import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import patch

# Import all models so they register with Base.metadata before create_all
import app.models.user  # noqa
import app.models.session  # noqa
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
from app.models.user import User
from app.services.auth_service import hash_password


TEST_USER_ID = "test-user-id-fixture"
TEST_ADMIN_ID = "test-admin-id-fixture"


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

    # Create test users
    test_user = User(
        id=TEST_USER_ID,
        email="testuser@example.com",
        username="testuser",
        hashed_password=hash_password("testpassword"),
        role="user",
        is_active=True,
        force_password_change=False,
    )
    test_admin = User(
        id=TEST_ADMIN_ID,
        email="admin@example.com",
        username="admin",
        hashed_password=hash_password("adminpassword"),
        role="admin",
        is_active=True,
        force_password_change=False,
    )
    session.add(test_user)
    session.add(test_admin)
    session.flush()

    buckets = [
        {"name": "Business", "priority": 10},
        {"name": "Documents", "priority": 5},
        {"name": "Personal", "priority": 20},
        {"name": "Trash", "priority": 100},
    ]
    for b in buckets:
        session.add(Bucket(
            id=str(uuid.uuid4()),
            user_id=TEST_USER_ID,
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
            user_id=TEST_USER_ID,
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
def test_user(db):
    """Return the test user object."""
    return db.query(User).filter(User.id == TEST_USER_ID).first()


@pytest.fixture
def test_admin(db):
    """Return the test admin object."""
    return db.query(User).filter(User.id == TEST_ADMIN_ID).first()


@pytest.fixture
def client(db, test_user):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return test_user

    def override_require_active_user():
        return test_user

    from app.dependencies import get_current_user, require_active_user, require_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_active_user] = override_require_active_user

    with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(db, test_admin):
    """Test client authenticated as admin."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return test_admin

    def override_require_active_user():
        return test_admin

    def override_require_admin():
        return test_admin

    from app.dependencies import get_current_user, require_active_user, require_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_active_user] = override_require_active_user
    app.dependency_overrides[require_admin] = override_require_admin

    with patch("app.main.init_db"), patch("app.main._bootstrap_admin"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()
