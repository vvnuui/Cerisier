from rest_framework import viewsets, generics, permissions
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Category, Tag, Post, Comment, FriendLink, SiteConfig
from .serializers import (
    CategorySerializer, TagSerializer,
    PostListSerializer, PostDetailSerializer,
    CommentSerializer, CommentCreateSerializer,
    FriendLinkSerializer, SiteConfigSerializer,
)


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """Public post API - only shows published posts"""
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        qs = Post.objects.filter(status="published").select_related(
            "category", "author"
        ).prefetch_related("tags")

        # Filter by category slug
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)

        # Filter by tag slug
        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__slug=tag)

        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PostDetailSerializer
        return PostListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        Post.objects.filter(pk=instance.pk).update(view_count=instance.view_count + 1)
        instance.view_count += 1
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class CategoryListView(generics.ListAPIView):
    """Public category list - returns tree structure (only top-level with children nested)"""
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(parent=None).annotate(
            post_count=Count("posts", filter=Q(posts__status="published"))
        ).prefetch_related("children")


class TagListView(generics.ListAPIView):
    """Public tag list with post counts"""
    permission_classes = [permissions.AllowAny]
    serializer_class = TagSerializer
    pagination_class = None

    def get_queryset(self):
        return Tag.objects.annotate(
            post_count=Count("posts", filter=Q(posts__status="published"))
        )


class ArchiveView(generics.ListAPIView):
    """Returns posts grouped by year-month for archive page"""
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        posts = Post.objects.filter(status="published").values(
            "title", "slug", "published_at"
        ).order_by("-published_at")

        archives = {}
        for post in posts:
            if post["published_at"]:
                key = post["published_at"].strftime("%Y-%m")
                if key not in archives:
                    archives[key] = []
                archives[key].append({
                    "title": post["title"],
                    "slug": post["slug"],
                    "published_at": post["published_at"],
                })

        return Response(archives)


class PostCommentListView(generics.ListAPIView):
    """GET /api/posts/{slug}/comments/ - returns approved comments for a post"""

    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Comment.objects.filter(
            post__slug=self.kwargs["slug"],
            is_approved=True,
            parent=None,  # Only top-level; replies nested via serializer
        ).select_related("user")


class PostCommentCreateView(generics.CreateAPIView):
    """POST /api/posts/{slug}/comments/ - submit a new comment (pending moderation)"""

    serializer_class = CommentCreateSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        post = Post.objects.get(slug=self.kwargs["slug"])
        user = self.request.user if self.request.user.is_authenticated else None
        # Admin comments are auto-approved
        is_approved = bool(user and user.role == "admin")
        serializer.save(post=post, user=user, is_approved=is_approved)


class FriendLinkListView(generics.ListAPIView):
    serializer_class = FriendLinkSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    queryset = FriendLink.objects.filter(is_active=True)


class SiteConfigView(generics.RetrieveAPIView):
    serializer_class = SiteConfigSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return SiteConfig.get_instance()
