import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_create_admin_user(self):
        user = User.objects.create_user(
            username="admin", email="admin@test.com", password="testpass123",
            role="admin"
        )
        assert user.role == "admin"
        assert user.is_active
        assert str(user) == "admin"

    def test_create_visitor(self):
        user = User.objects.create_user(
            username="visitor", email="v@test.com", password="testpass123",
            role="visitor"
        )
        assert user.role == "visitor"

    def test_default_role_is_visitor(self):
        user = User.objects.create_user(
            username="default", email="d@test.com", password="testpass123"
        )
        assert user.role == "visitor"
