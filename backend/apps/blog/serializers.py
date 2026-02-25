from rest_framework import serializers
from .models import Category, Tag, Post


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    post_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "parent", "sort_order", "children", "post_count"]

    def get_children(self, obj):
        # Only serialize children for top-level categories (avoid recursion in list)
        if obj.parent is None:
            children = obj.children.all()
            return CategorySerializer(children, many=True).data
        return []


class TagSerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "color", "post_count"]


class PostListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for post list (no full content)"""
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Post
        fields = [
            "id", "title", "slug", "excerpt", "cover_image",
            "category", "tags", "status", "is_pinned",
            "view_count", "like_count", "author_name",
            "created_at", "published_at",
        ]


class PostDetailSerializer(serializers.ModelSerializer):
    """Full serializer for post detail (includes content)"""
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Post
        fields = [
            "id", "title", "slug", "content", "content_markdown",
            "excerpt", "cover_image", "category", "tags",
            "status", "is_pinned", "view_count", "like_count",
            "author_name", "created_at", "updated_at", "published_at",
        ]
