"""Routing tree CRUD and hierarchy tests."""
import pytest
from app.services.routing_tree import RoutingTreeService, RoutingTreeError
from app.schemas.bucket import RoutingNodeCreate, RoutingNodeUpdate
from app.models.bucket import Bucket
from tests.conftest import TEST_USER_ID


def _seed_clean_tree(db):
    """Wipe the conftest-seeded buckets so each test starts empty."""
    db.query(Bucket).filter(Bucket.user_id == TEST_USER_ID).delete()
    db.commit()


def test_create_root_node(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    node = svc.create_node(RoutingNodeCreate(name="Business", is_leaf=True))
    assert node.name == "Business"
    assert node.path == "Business"
    assert node.parent_id is None
    assert node.is_leaf is True


def test_create_child_leaf(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    parent = svc.create_node(RoutingNodeCreate(name="Business", is_leaf=False))
    child = svc.create_node(
        RoutingNodeCreate(name="Job Photos", parent_id=parent.id, is_leaf=True)
    )
    assert child.path == "Business/Job Photos"
    assert child.parent_id == parent.id


def test_create_child_demotes_leaf_parent(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    parent = svc.create_node(RoutingNodeCreate(name="Business", is_leaf=True))
    svc.create_node(RoutingNodeCreate(name="Sub", parent_id=parent.id))
    db.refresh(parent)
    assert parent.is_leaf is False


def test_path_updates_on_rename(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    parent = svc.create_node(RoutingNodeCreate(name="Business", is_leaf=False))
    child = svc.create_node(
        RoutingNodeCreate(name="Job Photos", parent_id=parent.id, is_leaf=True)
    )
    grandchild = svc.create_node(
        RoutingNodeCreate(name="After", parent_id=child.id, is_leaf=True)
    )
    svc.rename_node(parent, "Work")
    db.refresh(parent)
    db.refresh(child)
    db.refresh(grandchild)
    assert parent.path == "Work"
    assert child.path == "Work/Job Photos"
    assert grandchild.path == "Work/Job Photos/After"


def test_duplicate_sibling_name_rejected(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    svc.create_node(RoutingNodeCreate(name="Business"))
    with pytest.raises(RoutingTreeError):
        svc.create_node(RoutingNodeCreate(name="Business"))


def test_disable_node_excludes_descendants_from_enabled_leaves(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    biz = svc.create_node(RoutingNodeCreate(name="Business", is_leaf=False))
    job = svc.create_node(
        RoutingNodeCreate(name="Job Photos", parent_id=biz.id, is_leaf=True)
    )
    leaves_before = {l.id for l in svc.get_enabled_leaves()}
    assert job.id in leaves_before

    svc.update_node(biz.id, RoutingNodeUpdate(enabled=False))
    leaves_after = {l.id for l in svc.get_enabled_leaves()}
    assert job.id not in leaves_after


def test_move_node_updates_paths(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    biz = svc.create_node(RoutingNodeCreate(name="Business", is_leaf=False))
    personal = svc.create_node(RoutingNodeCreate(name="Personal", is_leaf=False))
    leaf = svc.create_node(
        RoutingNodeCreate(name="Lake", parent_id=biz.id, is_leaf=True)
    )
    svc.move_node(leaf.id, personal.id)
    db.refresh(leaf)
    assert leaf.path == "Personal/Lake"


def test_cannot_move_node_into_descendant(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    a = svc.create_node(RoutingNodeCreate(name="A", is_leaf=False))
    b = svc.create_node(RoutingNodeCreate(name="B", parent_id=a.id, is_leaf=False))
    with pytest.raises(RoutingTreeError):
        svc.move_node(a.id, b.id)


def test_delete_with_children_requires_cascade(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    a = svc.create_node(RoutingNodeCreate(name="A", is_leaf=False))
    svc.create_node(RoutingNodeCreate(name="B", parent_id=a.id))
    with pytest.raises(RoutingTreeError):
        svc.delete_node(a.id)
    svc.delete_node(a.id, cascade=True)
    assert svc._get_or_none(a.id) is None


def test_invalid_destination_type(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    with pytest.raises(RoutingTreeError):
        svc.create_node(RoutingNodeCreate(name="X", destination_type="bogus"))


def test_invalid_privacy_rule(db):
    _seed_clean_tree(db)
    svc = RoutingTreeService(db, TEST_USER_ID)
    with pytest.raises(RoutingTreeError):
        svc.create_node(
            RoutingNodeCreate(name="X", privacy_rules={"faces_visible": "weird"})
        )
