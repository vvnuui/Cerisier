import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from apps.blog.models import Category, Post, Comment, FriendLink, SiteConfig

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def blog_data():
    user = User.objects.create_user(username="admin", password="test123", role="admin")
    post = Post.objects.create(
        title="Test Post",
        slug="test-post",
        content="<p>Test</p>",
        content_markdown="Test",
        author=user,
        status="published",
        published_at=timezone.now(),
    )
    return {"user": user, "post": post}


@pytest.mark.django_db
class TestCommentModel:
    def test_create_comment(self, blog_data):
        comment = Comment.objects.create(
            post=blog_data["post"],
            nickname="Visitor",
            email="v@test.com",
            content="Great post!",
        )
        assert str(comment) == "Visitor on Test Post"
        assert comment.is_approved is False

    def test_nested_comment(self, blog_data):
        parent = Comment.objects.create(
            post=blog_data["post"],
            nickname="A",
            email="a@test.com",
            content="Parent",
            is_approved=True,
        )
        reply = Comment.objects.create(
            post=blog_data["post"],
            nickname="B",
            email="b@test.com",
            content="Reply",
            parent=parent,
        )
        assert reply.parent == parent
        assert parent.replies.count() == 1


@pytest.mark.django_db
class TestCommentAPI:
    def test_list_approved_comments(self, api_client, blog_data):
        Comment.objects.create(
            post=blog_data["post"],
            nickname="A",
            email="a@t.com",
            content="Approved",
            is_approved=True,
        )
        Comment.objects.create(
            post=blog_data["post"],
            nickname="B",
            email="b@t.com",
            content="Pending",
            is_approved=False,
        )
        resp = api_client.get("/api/posts/test-post/comments/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["content"] == "Approved"

    def test_nested_replies_in_response(self, api_client, blog_data):
        parent = Comment.objects.create(
            post=blog_data["post"],
            nickname="A",
            email="a@t.com",
            content="Parent",
            is_approved=True,
        )
        Comment.objects.create(
            post=blog_data["post"],
            nickname="B",
            email="b@t.com",
            content="Reply",
            parent=parent,
            is_approved=True,
        )
        resp = api_client.get("/api/posts/test-post/comments/")
        assert len(resp.data) == 1  # Only top-level
        assert len(resp.data[0]["replies"]) == 1
        assert resp.data[0]["replies"][0]["content"] == "Reply"

    def test_anonymous_comment_requires_nickname(self, api_client, blog_data):
        resp = api_client.post(
            "/api/posts/test-post/comments/create/",
            {"content": "Hello", "email": "a@test.com"},
        )
        assert resp.status_code == 400

    def test_anonymous_comment_success(self, api_client, blog_data):
        resp = api_client.post(
            "/api/posts/test-post/comments/create/",
            {"content": "Great!", "nickname": "Visitor", "email": "v@test.com"},
        )
        assert resp.status_code == 201
        comment = Comment.objects.last()
        assert comment.is_approved is False  # Pending moderation
        assert comment.nickname == "Visitor"

    def test_admin_comment_auto_approved(self, api_client, blog_data):
        # Login as admin
        resp = api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": "test123"},
        )
        token = resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        resp = api_client.post(
            "/api/posts/test-post/comments/create/",
            {"content": "Admin reply"},
        )
        assert resp.status_code == 201
        comment = Comment.objects.last()
        assert comment.is_approved is True
        assert comment.user == blog_data["user"]


@pytest.mark.django_db
class TestFriendLinkAPI:
    def test_list_friend_links(self, api_client):
        FriendLink.objects.create(name="Blog A", url="https://a.com")
        FriendLink.objects.create(name="Blog B", url="https://b.com", is_active=False)
        resp = api_client.get("/api/friend-links/")
        assert resp.status_code == 200
        assert len(resp.data) == 1  # Only active


@pytest.mark.django_db
class TestSiteConfigAPI:
    def test_get_site_config(self, api_client):
        resp = api_client.get("/api/site-config/")
        assert resp.status_code == 200
        assert resp.data["site_name"] == "Cerisier"  # Default

    def test_site_config_singleton(self, api_client):
        SiteConfig.objects.create(site_name="My Blog")
        # Use save() instead of create() for the second instance
        # because create() passes force_insert=True which conflicts
        # with the singleton pk=1 override
        config = SiteConfig(site_name="Updated")
        config.save()  # Same pk=1
        assert SiteConfig.objects.count() == 1
        assert SiteConfig.objects.first().site_name == "Updated"
