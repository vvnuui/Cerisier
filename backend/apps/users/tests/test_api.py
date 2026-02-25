import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestJWTAuth:
    def setup_method(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", role="admin"
        )

    def test_obtain_token(self):
        resp = self.client.post("/api/auth/token/", {
            "username": "admin", "password": "testpass123"
        })
        assert resp.status_code == 200
        assert "access" in resp.data
        assert "refresh" in resp.data

    def test_obtain_token_wrong_password(self):
        resp = self.client.post("/api/auth/token/", {
            "username": "admin", "password": "wrongpass"
        })
        assert resp.status_code == 401

    def test_refresh_token(self):
        resp = self.client.post("/api/auth/token/", {
            "username": "admin", "password": "testpass123"
        })
        refresh_token = resp.data["refresh"]
        resp2 = self.client.post("/api/auth/token/refresh/", {
            "refresh": refresh_token
        })
        assert resp2.status_code == 200
        assert "access" in resp2.data

    def test_current_user_authenticated(self):
        resp = self.client.post("/api/auth/token/", {
            "username": "admin", "password": "testpass123"
        })
        token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp2 = self.client.get("/api/auth/me/")
        assert resp2.status_code == 200
        assert resp2.data["username"] == "admin"
        assert resp2.data["role"] == "admin"

    def test_current_user_unauthenticated(self):
        resp = self.client.get("/api/auth/me/")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestIsAdminPermission:
    def setup_method(self):
        self.client = APIClient()
        self.visitor = User.objects.create_user(
            username="visitor", password="testpass123", role="visitor"
        )

    def test_visitor_cannot_access_admin_endpoint(self):
        # This will be useful when we add admin-only endpoints later
        # For now just verify the permission class works
        from apps.users.permissions import IsAdmin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = self.visitor
        permission = IsAdmin()
        assert not permission.has_permission(request, None)
