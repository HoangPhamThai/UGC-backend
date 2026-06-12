import pytest

from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import Product


def _doc(**overrides):
    base = {
        "_id": "u_1",
        "email": "qc@example.com",
        "password_hashed": "x",
        "role": "qc",
    }
    base.update(overrides)
    return base


def test_accepts_legacy_singular_qc_product():
    # Legacy docs stored a scalar `qc_product`; the model must coerce it.
    u = User.model_validate(_doc(qc_product="CL"))
    assert u.qc_products == [Product.CL]


def test_legacy_qc_product_does_not_override_existing_plural():
    u = User.model_validate(_doc(qc_products=["MMF"], qc_product="CL"))
    assert u.qc_products == [Product.MMF]


def test_plural_qc_products_still_works():
    u = User.model_validate(_doc(qc_products=["CL", "MMF"]))
    assert set(u.qc_products) == {Product.CL, Product.MMF}


def test_qc_without_any_products_still_raises():
    with pytest.raises(Exception):
        User.model_validate(_doc())  # role=qc, no qc_products and no qc_product


def test_legacy_field_ignored_for_non_qc_roles():
    # A stray scalar on a non-qc role must not produce qc_products (which would
    # then violate the "must be empty when role != qc" rule).
    u = User.model_validate(
        {"_id": "u_2", "email": "c@example.com", "password_hashed": "x",
         "role": "creator", "qc_product": "CL"}
    )
    assert u.qc_products == []
