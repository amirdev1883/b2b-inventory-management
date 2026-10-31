import pytest
from apps.users.models import Tenant, User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/auth/csrf/").data["csrfToken"]
    client.credentials(HTTP_X_CSRFTOKEN=token)
    return client


def test_registration_creates_business_admin():
    client = csrf_client()
    response = client.post(
        "/api/auth/register/",
        {
            "business_name": "Acme",
            "currency": "USD",
            "email": "TEST@Example.com",
            "first_name": "Test",
            "password": "Secure-8324-long!",
        },
    )
    assert response.status_code == 201
    assert response.data["user"]["role"] == "ADMIN"
    assert response.data["business"]["currency"] == "USD"
    user = User.objects.get(email="test@example.com")
    assert user.check_password("Secure-8324-long!")
    assert not user.is_staff
    assert "password" not in response.data["user"]
    assert response.cookies["b2b_refresh"]["httponly"]
    assert response.cookies["b2b_refresh"]["samesite"] == "Lax"


def test_auth_endpoints_require_csrf(admin):
    client = APIClient(enforce_csrf_checks=True)
    for endpoint in [
        "login",
        "register",
        "refresh",
        "logout",
        "password-reset",
        "password-reset/confirm",
    ]:
        assert client.post(f"/api/auth/{endpoint}/", {}).status_code == 403


def test_weak_password_and_duplicate_registration(admin):
    client = csrf_client()
    data = {
        "business_name": "Acme",
        "email": "new@example.com",
        "first_name": "A",
        "password": "password123",
    }
    assert client.post("/api/auth/register/", data).status_code == 400
    data.update(email="OWNER@example.com", password="Secure-8324-long!")
    assert client.post("/api/auth/register/", data).status_code == 400
    assert Tenant.objects.count() == 1


def test_login_refresh_rotation_and_logout(admin):
    client = csrf_client()
    response = client.post(
        "/api/auth/login/", {"email": "OWNER@example.com", "password": "A-real-password-832!"}
    )
    assert response.status_code == 200
    first_refresh = client.cookies["b2b_refresh"].value
    client.credentials(
        HTTP_X_CSRFTOKEN=client.get("/api/auth/csrf/").data["csrfToken"],
        HTTP_AUTHORIZATION=f"Bearer {response.data['access']}",
    )
    assert client.get("/api/auth/me/").status_code == 200
    assert client.post("/api/auth/refresh/", {}).status_code == 200
    new_refresh = client.cookies["b2b_refresh"].value
    assert new_refresh != first_refresh
    client.cookies["b2b_refresh"] = first_refresh
    assert client.post("/api/auth/refresh/", {}).status_code == 401
    client.cookies["b2b_refresh"] = new_refresh
    assert client.post("/api/auth/logout/", {}).status_code == 204
    client.cookies["b2b_refresh"] = new_refresh
    assert client.post("/api/auth/refresh/", {}).status_code == 401


def test_invalid_login_and_inactive_business(admin):
    client = csrf_client()
    assert (
        client.post("/api/auth/login/", {"email": admin.email, "password": "wrong"}).status_code
        == 401
    )
    admin.tenant.is_active = False
    admin.tenant.save()
    assert (
        client.post(
            "/api/auth/login/", {"email": admin.email, "password": "A-real-password-832!"}
        ).status_code
        == 401
    )


def test_token_rechecks_active_user_and_tenant(admin):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(admin)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    assert client.get("/api/products/").status_code == 200
    admin.tenant.is_active = False
    admin.tenant.save()
    assert client.get("/api/products/").status_code == 401


def test_password_reset_generic_response_and_single_use(admin):
    client = csrf_client()
    existing = client.post("/api/auth/password-reset/", {"email": admin.email})
    missing = client.post("/api/auth/password-reset/", {"email": "missing@example.com"})
    assert existing.data == missing.data
    assert len(mail.outbox) == 1
    token = default_token_generator.make_token(admin)
    payload = {
        "uid": urlsafe_base64_encode(force_bytes(admin.pk)),
        "token": token,
        "password": "A-new-password-938!",
    }
    assert client.post("/api/auth/password-reset/confirm/", payload).status_code == 200
    assert client.post("/api/auth/password-reset/confirm/", payload).status_code == 400
    admin.refresh_from_db()
    assert admin.check_password(payload["password"])


def test_password_change_revokes_access_and_refresh(admin):
    client = csrf_client()
    response = client.post(
        "/api/auth/login/", {"email": admin.email, "password": "A-real-password-832!"}
    )
    admin.set_password("Another-pass-389!")
    admin.save()
    client.credentials(
        HTTP_X_CSRFTOKEN=client.get("/api/auth/csrf/").data["csrfToken"],
        HTTP_AUTHORIZATION=f"Bearer {response.data['access']}",
    )
    assert client.get("/api/auth/me/").status_code == 401
    assert client.post("/api/auth/refresh/", {}).status_code == 401


def test_last_admin_protection(client, admin, staff):
    assert client.patch(f"/api/users/{admin.pk}/", {"is_active": False}).status_code == 400
    assert client.patch(f"/api/users/{admin.pk}/", {"role": "STAFF"}).status_code == 400
    assert client.patch(f"/api/users/{staff.pk}/", {"role": "ADMIN"}).status_code == 200
    assert client.patch(f"/api/users/{admin.pk}/", {"role": "MANAGER"}).status_code == 200


def test_user_creation_tenant_and_no_privilege_escalation(client, tenant):
    response = client.post(
        "/api/users/",
        {
            "email": "another@example.com",
            "password": "Long-Password-8324!",
            "role": "MANAGER",
            "is_superuser": True,
            "is_staff": True,
        },
    )
    assert response.status_code == 201
    user = User.objects.get(email="another@example.com")
    assert user.tenant == tenant
    assert not user.is_superuser and not user.is_staff


@pytest.mark.parametrize(
    "resource",
    ["products", "suppliers", "sales-orders", "purchase-orders", "stock-movements", "users"],
)
def test_anonymous_api_denied(resource):
    assert APIClient().get(f"/api/{resource}/").status_code == 401


def test_change_password_checks_current_password_and_rotates_session(client, admin):
    wrong = client.post(
        "/api/auth/password-change/",
        {"current_password": "wrong", "new_password": "New-Secure-pass-839!"},
    )
    assert wrong.status_code == 400
    response = client.post(
        "/api/auth/password-change/",
        {"current_password": "A-real-password-832!", "new_password": "New-Secure-pass-839!"},
    )
    assert response.status_code == 200
    assert response.data["access"]
    assert response.cookies["b2b_refresh"]["httponly"]
    admin.refresh_from_db()
    assert admin.check_password("New-Secure-pass-839!")
