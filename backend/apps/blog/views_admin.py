from django.db import models
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.utils import timezone
from apps.users.permissions import IsAdmin
from .models import Category, Tag, Post, Comment, SiteConfig
from .serializers import (
    AdminPostSerializer, AdminCategorySerializer,
    AdminTagSerializer, AdminCommentSerializer,
    SiteConfigSerializer,
)


class AdminPostViewSet(viewsets.ModelViewSet):
    """Admin CRUD for posts"""
    serializer_class = AdminPostSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = Post.objects.select_related("category", "author").prefetch_related("tags")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        # Auto-set published_at when publishing
        instance = serializer.instance
        new_status = serializer.validated_data.get("status")
        if new_status == "published" and instance.status != "published":
            serializer.save(published_at=timezone.now())
        else:
            serializer.save()


class AdminCategoryViewSet(viewsets.ModelViewSet):
    """Admin CRUD for categories"""
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAdmin]
    queryset = Category.objects.all()


class AdminTagViewSet(viewsets.ModelViewSet):
    """Admin CRUD for tags"""
    serializer_class = AdminTagSerializer
    permission_classes = [IsAdmin]
    queryset = Tag.objects.all()


class AdminCommentViewSet(viewsets.ModelViewSet):
    """Admin comment moderation"""
    serializer_class = AdminCommentSerializer
    permission_classes = [IsAdmin]
    queryset = Comment.objects.select_related("user", "post").order_by("-created_at")
    http_method_names = ["get", "patch", "delete", "head", "options"]
    # Only allow GET (list/detail), PATCH (approve), DELETE


class AdminSiteConfigView(generics.RetrieveUpdateAPIView):
    """Admin site settings"""
    serializer_class = SiteConfigSerializer
    permission_classes = [IsAdmin]

    def get_object(self):
        return SiteConfig.get_instance()


class ImageUploadView(generics.CreateAPIView):
    """Upload an image and return the URL"""
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        file = request.FILES.get("image")
        if not file:
            return Response(
                {"error": "No image file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Save to media/uploads/
        from django.core.files.storage import default_storage
        path = default_storage.save(f"uploads/{file.name}", file)
        url = request.build_absolute_uri(f"/media/{path}")
        return Response({"url": url}, status=status.HTTP_201_CREATED)


class DashboardView(APIView):
    """GET /api/admin/dashboard/ - returns blog stats"""
    permission_classes = [IsAdmin]

    def get(self, request):
        # Basic stats
        total_posts = Post.objects.count()
        published_posts = Post.objects.filter(status="published").count()
        total_views = Post.objects.aggregate(total=Sum("view_count"))["total"] or 0
        total_comments = Comment.objects.count()
        pending_comments = Comment.objects.filter(is_approved=False).count()

        # Posts by month (last 12 months)
        posts_by_month = list(
            Post.objects.filter(status="published")
            .annotate(month=TruncMonth("published_at"))
            .values("month")
            .annotate(count=models.Count("id"))
            .order_by("month")
        )
        # Convert to serializable format
        posts_by_month = [
            {"month": item["month"].strftime("%Y-%m") if item["month"] else None,
             "count": item["count"]}
            for item in posts_by_month
        ]

        # Recent comments (last 5)
        recent_comments = list(
            Comment.objects.select_related("post", "user")
            .order_by("-created_at")[:5]
            .values("id", "content", "nickname", "is_approved", "created_at",
                    "post__title", "post__slug")
        )

        return Response({
            "total_posts": total_posts,
            "published_posts": published_posts,
            "total_views": total_views,
            "total_comments": total_comments,
            "pending_comments": pending_comments,
            "posts_by_month": posts_by_month,
            "recent_comments": recent_comments,
        })
