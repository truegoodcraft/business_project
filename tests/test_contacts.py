# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest

pytestmark = pytest.mark.api


@pytest.fixture()
def contacts_client(bus_client):
    """Use the product's canonical isolated schema/bootstrap fixture."""

    with bus_client["engine"].SessionLocal() as db:
        db.query(bus_client["models"].Vendor).delete()
        db.commit()
    return bus_client


def test_get_contacts_returns_empty_list(contacts_client):
    client = contacts_client["client"]

    resp = client.get("/app/contacts")

    assert resp.status_code == 200
    assert resp.json() == []


def test_create_contact_defaults_to_flags_false(contacts_client):
    client = contacts_client["client"]

    resp = client.post("/app/contacts", json={"name": "Alice"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Alice"
    assert data["is_vendor"] is False
    assert data["is_org"] is False

    vendor_resp = client.post("/app/contacts", json={"name": "Bob", "is_vendor": True})
    assert vendor_resp.status_code == 201


def test_contact_filters_by_vendor_and_org_flags(contacts_client):
    client = contacts_client["client"]
    engine = contacts_client["engine"]
    models = contacts_client["models"]

    with engine.SessionLocal() as db:
        db.query(models.Vendor).delete()
        db.add_all(
            [
                models.Vendor(name="Bob", is_vendor=1, role="vendor"),
                models.Vendor(name="Carol", is_vendor=0, role="contact"),
                models.Vendor(name="OrgCo", is_vendor=0, is_org=1, role="contact"),
            ]
        )
        db.commit()
        names = {v.name for v in db.query(models.Vendor).all()}
        assert names == {"Bob", "Carol", "OrgCo"}

    vendors = client.get("/app/contacts", params={"is_vendor": "true"})
    assert vendors.status_code == 200
    assert {v["name"] for v in vendors.json()} == {"Bob"}

    non_vendors = client.get("/app/contacts", params={"is_vendor": "false"})
    assert non_vendors.status_code == 200
    assert {v["name"] for v in non_vendors.json()} == {"Carol", "OrgCo"}

    orgs = client.get("/app/contacts", params={"is_org": "true"})
    assert orgs.status_code == 200
    assert {v["name"] for v in orgs.json()} == {"OrgCo"}

    # Verify vendor endpoint with same filters still works
    vendor_orgs = client.get("/app/vendors", params={"is_org": "true"})
    assert vendor_orgs.status_code == 200
    assert {v["name"] for v in vendor_orgs.json()} == {"OrgCo"}
