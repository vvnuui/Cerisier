import pytest
from django.contrib.auth import get_user_model
from apps.blog.models import Category, Tag, Post

User = get_user_model()


@pytest.mark.django_db
class TestCategory:
    def test_create_category(self):
        cat = Category.objects.create(name="Python", slug="python", description="Python posts")
        assert str(cat) == "Python"
        assert cat.slug == "python"

    def test_category_tree(self):
        parent = Category.objects.create(name="Tech", slug="tech")
        child = Category.objects.create(name="Python", slug="python", parent=parent)
        assert child.parent == parent
        assert parent.children.count() == 1

    def test_category_ordering(self):
        cat2 = Category.objects.create(name="B", slug="b", sort_order=2)
        cat1 = Category.objects.create(name="A", slug="a", sort_order=1)
        cats = list(Category.objects.all())
        assert cats[0] == cat1
        assert cats[1] == cat2


@pytest.mark.django_db
class TestTag:
    def test_create_tag(self):
        tag = Tag.objects.create(name="Django", slug="django")
        assert str(tag) == "Django"
        assert tag.color == "#3b82f6"  # default color

    def test_tag_custom_color(self):
        tag = Tag.objects.create(name="Vue", slug="vue", color="#42b883")
        assert tag.color == "#42b883"


@pytest.mark.django_db
class TestPost:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.user = User.objects.create_user(username="author", password="test123", role="admin")
        self.category = Category.objects.create(name="Tech", slug="tech")
        self.tag = Tag.objects.create(name="Python", slug="python")

    def test_create_draft_post(self):
        post = Post.objects.create(
            title="Test Post", slug="test-post",
            content="<p>Hello</p>", content_markdown="Hello",
            author=self.user, category=self.category
        )
        assert str(post) == "Test Post"
        assert post.status == "draft"
        assert post.view_count == 0
        assert post.is_pinned is False

    def test_post_with_tags(self):
        post = Post.objects.create(
            title="Tagged Post", slug="tagged-post",
            content="content", content_markdown="content",
            author=self.user
        )
        post.tags.add(self.tag)
        assert self.tag in post.tags.all()

    def test_post_published(self):
        from django.utils import timezone
        post = Post.objects.create(
            title="Published", slug="published",
            content="content", content_markdown="content",
            author=self.user, status="published",
            published_at=timezone.now()
        )
        assert post.status == "published"
        assert post.published_at is not None

    def test_post_ordering(self):
        """Posts should be ordered by -is_pinned, -created_at (pinned first, newest first)"""
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()

        p1 = Post.objects.create(
            title="Old", slug="old", content="c", content_markdown="c",
            author=self.user
        )
        # Force distinct created_at values (auto_now_add prevents direct assignment)
        Post.objects.filter(pk=p1.pk).update(created_at=now - timedelta(hours=2))

        p2 = Post.objects.create(
            title="New", slug="new", content="c", content_markdown="c",
            author=self.user
        )
        Post.objects.filter(pk=p2.pk).update(created_at=now - timedelta(hours=1))

        p3 = Post.objects.create(
            title="Pinned", slug="pinned", content="c", content_markdown="c",
            author=self.user, is_pinned=True
        )
        Post.objects.filter(pk=p3.pk).update(created_at=now - timedelta(hours=3))

        posts = list(Post.objects.all())
        assert posts[0] == p3  # pinned first
        assert posts[1] == p2  # then newest (created_at = now - 1h)
        assert posts[2] == p1  # then oldest (created_at = now - 2h)

    def test_post_category_set_null(self):
        """When category is deleted, post.category should be set to NULL"""
        post = Post.objects.create(
            title="Test", slug="test", content="c", content_markdown="c",
            author=self.user, category=self.category
        )
        self.category.delete()
        post.refresh_from_db()
        assert post.category is None
