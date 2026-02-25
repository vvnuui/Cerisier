from rest_framework import serializers
from .models import Category, Tag, Post, Comment, FriendLink, SiteConfig


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


class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id", "post", "author_name", "content", "parent",
            "replies", "is_approved", "created_at",
        ]
        read_only_fields = ["id", "is_approved", "created_at"]

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(
                obj.replies.filter(is_approved=True), many=True
            ).data
        return []

    def get_author_name(self, obj):
        if obj.user:
            return obj.user.username
        return obj.nickname


class CommentCreateSerializer(serializers.ModelSerializer):
    """For submitting new comments (anonymous or authenticated)"""

    class Meta:
        model = Comment
        fields = ["post", "content", "parent", "nickname", "email"]
        extra_kwargs = {"post": {"required": False}}

    def validate(self, data):
        # Anonymous comments must have nickname and email
        request = self.context.get("request")
        if not (request and request.user.is_authenticated):
            if not data.get("nickname"):
                raise serializers.ValidationError(
                    {"nickname": "Anonymous comments require a nickname."}
                )
            if not data.get("email"):
                raise serializers.ValidationError(
                    {"email": "Anonymous comments require an email."}
                )
        return data


class FriendLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = FriendLink
        fields = ["id", "name", "url", "description", "logo"]


class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        fields = ["site_name", "site_description", "site_logo", "github_url", "email"]
