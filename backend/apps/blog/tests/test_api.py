import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from apps.blog.models import Category, Tag, Post

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_data():
    user = User.objects.create_user(username="author", password="test123", role="admin")
    cat = Category.objects.create(name="Tech", slug="tech")
    child_cat = Category.objects.create(name="Python", slug="python", parent=cat)
    tag1 = Tag.objects.create(name="Django", slug="django")
    tag2 = Tag.objects.create(name="Vue", slug="vue", color="#42b883")

    published = Post.objects.create(
        title="Published Post", slug="published-post",
        content="<p>Hello World</p>", content_markdown="Hello World",
        excerpt="A published post", author=user, category=cat,
        status="published", published_at=timezone.now(),
    )
    published.tags.add(tag1)

    draft = Post.objects.create(
        title="Draft Post", slug="draft-post",
        content="<p>Draft</p>", content_markdown="Draft",
        author=user, status="draft",
    )

    return {
        "user": user, "category": cat, "child_category": child_cat,
        "tag1": tag1, "tag2": tag2,
        "published": published, "draft": draft,
    }


@pytest.mark.django_db
class TestPostAPI:
    def test_list_only_published(self, api_client, sample_data):
        resp = api_client.get("/api/posts/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["title"] == "Published Post"

    def test_list_excludes_drafts(self, api_client, sample_data):
        resp = api_client.get("/api/posts/")
        slugs = [p["slug"] for p in resp.data["results"]]
        assert "draft-post" not in slugs

    def test_detail_by_slug(self, api_client, sample_data):
        resp = api_client.get("/api/posts/published-post/")
        assert resp.status_code == 200
        assert resp.data["title"] == "Published Post"
        assert resp.data["content"] == "<p>Hello World</p>"
        assert "content_markdown" in resp.data  # detail includes markdown

    def test_detail_increments_view_count(self, api_client, sample_data):
        api_client.get("/api/posts/published-post/")
        api_client.get("/api/posts/published-post/")
        sample_data["published"].refresh_from_db()
        assert sample_data["published"].view_count == 2

    def test_filter_by_category(self, api_client, sample_data):
        resp = api_client.get("/api/posts/?category=tech")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_filter_by_tag(self, api_client, sample_data):
        resp = api_client.get("/api/posts/?tag=django")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_filter_by_nonexistent_tag(self, api_client, sample_data):
        resp = api_client.get("/api/posts/?tag=nonexistent")
        assert resp.status_code == 200
        assert resp.data["count"] == 0

    def test_draft_not_accessible(self, api_client, sample_data):
        resp = api_client.get("/api/posts/draft-post/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestCategoryAPI:
    def test_list_categories_tree(self, api_client, sample_data):
        resp = api_client.get("/api/categories/")
        assert resp.status_code == 200
        # Should only return top-level categories
        assert len(resp.data) == 1  # Only "Tech" (top-level), not paginated
        tech = resp.data[0]
        assert tech["name"] == "Tech"
        assert len(tech["children"]) == 1
        assert tech["children"][0]["name"] == "Python"

    def test_category_post_count(self, api_client, sample_data):
        resp = api_client.get("/api/categories/")
        tech = resp.data[0]
        assert tech["post_count"] == 1  # One published post in Tech


@pytest.mark.django_db
class TestTagAPI:
    def test_list_tags(self, api_client, sample_data):
        resp = api_client.get("/api/tags/")
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_tag_post_count(self, api_client, sample_data):
        resp = api_client.get("/api/tags/")
        django_tag = next(t for t in resp.data if t["name"] == "Django")
        assert django_tag["post_count"] == 1


@pytest.mark.django_db
class TestArchiveAPI:
    def test_archive_grouped_by_month(self, api_client, sample_data):
        resp = api_client.get("/api/archives/")
        assert resp.status_code == 200
        # Should have one month group with the published post
        assert len(resp.data) >= 1
        month_key = list(resp.data.keys())[0]
        assert len(resp.data[month_key]) == 1
        assert resp.data[month_key][0]["title"] == "Published Post"
