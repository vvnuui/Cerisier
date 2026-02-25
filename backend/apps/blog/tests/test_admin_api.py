import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from apps.blog.models import Category, Tag, Post, Comment

User = get_user_model()


@pytest.fixture
def admin_client():
    user = User.objects.create_user(username="admin", password="test123", role="admin")
    client = APIClient()
    resp = client.post("/api/auth/token/", {"username": "admin", "password": "test123"})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client, user


@pytest.fixture
def visitor_client():
    User.objects.create_user(username="visitor", password="test123", role="visitor")
    client = APIClient()
    resp = client.post("/api/auth/token/", {"username": "visitor", "password": "test123"})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.mark.django_db
class TestAdminPostCRUD:
    def test_create_draft(self, admin_client):
        client, user = admin_client
        resp = client.post("/api/admin/posts/", {
            "title": "New Post",
            "slug": "new-post",
            "content": "<p>Hello</p>",
            "content_markdown": "Hello",
        })
        assert resp.status_code == 201
        assert resp.data["status"] == "draft"
        post = Post.objects.get(slug="new-post")
        assert post.author == user

    def test_publish_post(self, admin_client):
        client, user = admin_client
        post = Post.objects.create(
            title="Draft", slug="draft", content="c", content_markdown="c",
            author=user, status="draft",
        )
        resp = client.patch(f"/api/admin/posts/{post.id}/", {
            "status": "published",
        })
        assert resp.status_code == 200
        post.refresh_from_db()
        assert post.status == "published"
        assert post.published_at is not None

    def test_archive_post(self, admin_client):
        client, user = admin_client
        post = Post.objects.create(
            title="Published", slug="pub", content="c", content_markdown="c",
            author=user, status="published", published_at=timezone.now(),
        )
        resp = client.patch(f"/api/admin/posts/{post.id}/", {
            "status": "archived",
        })
        assert resp.status_code == 200
        post.refresh_from_db()
        assert post.status == "archived"

    def test_create_with_tags(self, admin_client):
        client, user = admin_client
        tag = Tag.objects.create(name="Python", slug="python")
        resp = client.post("/api/admin/posts/", {
            "title": "Tagged", "slug": "tagged",
            "content": "c", "content_markdown": "c",
            "tag_ids": [tag.id],
        })
        assert resp.status_code == 201
        post = Post.objects.get(slug="tagged")
        assert tag in post.tags.all()

    def test_delete_post(self, admin_client):
        client, user = admin_client
        post = Post.objects.create(
            title="Delete Me", slug="delete-me", content="c", content_markdown="c",
            author=user,
        )
        resp = client.delete(f"/api/admin/posts/{post.id}/")
        assert resp.status_code == 204
        assert not Post.objects.filter(id=post.id).exists()

    def test_visitor_cannot_create(self, visitor_client):
        resp = visitor_client.post("/api/admin/posts/", {
            "title": "Nope", "slug": "nope", "content": "c", "content_markdown": "c",
        })
        assert resp.status_code == 403

    def test_filter_by_status(self, admin_client):
        client, user = admin_client
        Post.objects.create(
            title="Draft", slug="d", content="c", content_markdown="c",
            author=user, status="draft",
        )
        Post.objects.create(
            title="Published", slug="p", content="c", content_markdown="c",
            author=user, status="published", published_at=timezone.now(),
        )
        resp = client.get("/api/admin/posts/?status=draft")
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["title"] == "Draft"


@pytest.mark.django_db
class TestAdminCategoryCRUD:
    def test_create_category(self, admin_client):
        client, _ = admin_client
        resp = client.post("/api/admin/categories/", {
            "name": "Tech", "slug": "tech",
        })
        assert resp.status_code == 201

    def test_update_category(self, admin_client):
        client, _ = admin_client
        cat = Category.objects.create(name="Old", slug="old")
        resp = client.patch(f"/api/admin/categories/{cat.id}/", {"name": "New"})
        assert resp.status_code == 200
        cat.refresh_from_db()
        assert cat.name == "New"

    def test_delete_category(self, admin_client):
        client, _ = admin_client
        cat = Category.objects.create(name="Delete", slug="delete")
        resp = client.delete(f"/api/admin/categories/{cat.id}/")
        assert resp.status_code == 204


@pytest.mark.django_db
class TestAdminTagCRUD:
    def test_create_tag(self, admin_client):
        client, _ = admin_client
        resp = client.post("/api/admin/tags/", {
            "name": "Vue", "slug": "vue", "color": "#42b883",
        })
        assert resp.status_code == 201

    def test_delete_tag(self, admin_client):
        client, _ = admin_client
        tag = Tag.objects.create(name="Delete", slug="delete")
        resp = client.delete(f"/api/admin/tags/{tag.id}/")
        assert resp.status_code == 204


@pytest.mark.django_db
class TestAdminCommentModeration:
    def test_approve_comment(self, admin_client):
        client, user = admin_client
        post = Post.objects.create(
            title="Post", slug="post", content="c", content_markdown="c",
            author=user, status="published", published_at=timezone.now(),
        )
        comment = Comment.objects.create(
            post=post, nickname="Visitor", email="v@t.com",
            content="Hello", is_approved=False,
        )
        resp = client.patch(f"/api/admin/comments/{comment.id}/", {
            "is_approved": True,
        })
        assert resp.status_code == 200
        comment.refresh_from_db()
        assert comment.is_approved is True

    def test_delete_comment(self, admin_client):
        client, user = admin_client
        post = Post.objects.create(
            title="Post", slug="post", content="c", content_markdown="c",
            author=user, status="published", published_at=timezone.now(),
        )
        comment = Comment.objects.create(
            post=post, nickname="Spam", email="s@t.com", content="Buy now!",
        )
        resp = client.delete(f"/api/admin/comments/{comment.id}/")
        assert resp.status_code == 204

    def test_list_all_comments(self, admin_client):
        client, user = admin_client
        post = Post.objects.create(
            title="Post", slug="post", content="c", content_markdown="c",
            author=user, status="published", published_at=timezone.now(),
        )
        Comment.objects.create(post=post, nickname="A", email="a@t.com", content="Approved", is_approved=True)
        Comment.objects.create(post=post, nickname="B", email="b@t.com", content="Pending", is_approved=False)
        resp = client.get("/api/admin/comments/")
        assert resp.data["count"] == 2  # Admin sees all comments
