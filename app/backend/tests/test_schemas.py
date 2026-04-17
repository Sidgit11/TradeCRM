"""Tests for Pydantic request/response schema validation."""
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.auth import SignupRequest, LoginRequest, TenantUpdateRequest, InviteMemberRequest
from app.schemas.contacts import ContactCreate, ContactUpdate, ContactListCreate
from app.schemas.companies import CompanyCreate, CompanyUpdate


class TestSignupSchema:
    def test_valid_signup(self):
        req = SignupRequest(
            company_name="Spice Exports",
            name="Rajesh Kumar",
            email="rajesh@spiceexports.com",
            password="secure_password_123",
        )
        assert req.company_name == "Spice Exports"

    def test_rejects_short_company_name(self):
        with pytest.raises(ValidationError):
            SignupRequest(company_name="X", name="Rajesh", email="r@t.com", password="12345678")

    def test_rejects_short_password(self):
        with pytest.raises(ValidationError):
            SignupRequest(company_name="Test Co", name="User", email="u@t.com", password="short")

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            SignupRequest(company_name="Test Co", name="User", email="not-email", password="12345678")

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            SignupRequest(company_name="Test Co", name="", email="u@t.com", password="12345678")


class TestLoginSchema:
    def test_valid_login(self):
        req = LoginRequest(email="user@test.com", password="password123")
        assert req.email == "user@test.com"

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="bad", password="password")


class TestContactCreateSchema:
    def test_valid_contact_minimal(self):
        c = ContactCreate(name="Hans Mueller")
        assert c.name == "Hans Mueller"
        assert c.tags == []
        assert c.opted_in_email is True
        assert c.opted_in_whatsapp is False

    def test_valid_contact_full(self):
        c = ContactCreate(
            name="Hans Mueller",
            email="hans@test.de",
            phone="+49170123456",
            company_name="German Importer",
            title="Purchasing Manager",
            tags=["pepper", "EU"],
            custom_fields={"lang": "en"},
            opted_in_whatsapp=True,
        )
        assert len(c.tags) == 2
        assert c.phone == "+49170123456"

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="")

    def test_defaults_source_to_manual(self):
        c = ContactCreate(name="Test")
        assert c.source == "manual"


class TestContactUpdateSchema:
    def test_partial_update(self):
        u = ContactUpdate(name="Updated Name")
        data = u.model_dump(exclude_unset=True)
        assert data == {"name": "Updated Name"}
        assert "email" not in data

    def test_empty_update_has_no_fields(self):
        u = ContactUpdate()
        data = u.model_dump(exclude_unset=True)
        assert data == {}


class TestContactListCreateSchema:
    def test_valid_list(self):
        cl = ContactListCreate(name="EU Pepper Buyers")
        assert cl.name == "EU Pepper Buyers"
        assert cl.description is None

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            ContactListCreate(name="")


class TestCompanyCreateSchema:
    def test_valid_company_minimal(self):
        c = CompanyCreate(name="Euro Spice BV")
        assert c.name == "Euro Spice BV"
        assert c.commodities == []

    def test_valid_company_full(self):
        c = CompanyCreate(
            name="Euro Spice BV",
            country="Netherlands",
            website="https://eurospice.nl",
            industry="Spice Import",
            commodities=["pepper", "turmeric"],
            import_volume_annual=5_000_000,
            shipment_frequency="monthly",
            source="discovery",
        )
        assert c.import_volume_annual == 5_000_000
        assert len(c.commodities) == 2

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            CompanyCreate(name="")


class TestCompanyUpdateSchema:
    def test_partial_update(self):
        u = CompanyUpdate(country="Germany")
        data = u.model_dump(exclude_unset=True)
        assert data == {"country": "Germany"}


class TestTenantUpdateSchema:
    def test_partial_update(self):
        u = TenantUpdateRequest(commodities=["pepper", "cloves"])
        data = u.model_dump(exclude_unset=True)
        assert data == {"commodities": ["pepper", "cloves"]}
        assert "company_name" not in data


class TestInviteMemberSchema:
    def test_valid_invite(self):
        i = InviteMemberRequest(email="new@test.com", name="New Member")
        assert i.role == "member"

    def test_admin_invite(self):
        i = InviteMemberRequest(email="admin@test.com", name="Admin", role="admin")
        assert i.role == "admin"

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            InviteMemberRequest(email="bad", name="Test")
