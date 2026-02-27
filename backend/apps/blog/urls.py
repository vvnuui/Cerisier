from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_admin

router = DefaultRouter()
router.register(r"posts", views.PostViewSet, basename="post")

admin_router = DefaultRouter()
admin_router.register(r"posts", views_admin.AdminPostViewSet, basename="admin-post")
admin_router.register(r"categories", views_admin.AdminCategoryViewSet, basename="admin-category")
admin_router.register(r"tags", views_admin.AdminTagViewSet, basename="admin-tag")
admin_router.register(r"comments", views_admin.AdminCommentViewSet, basename="admin-comment")

urlpatterns = [
    # Public API
    path("", include(router.urls)),
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("tags/", views.TagListView.as_view(), name="tag-list"),
    path("archives/", views.ArchiveView.as_view(), name="archive-list"),
    path("posts/<slug:slug>/comments/", views.PostCommentListView.as_view(), name="post-comments"),
    path("posts/<slug:slug>/comments/create/", views.PostCommentCreateView.as_view(), name="post-comment-create"),
    path("friend-links/", views.FriendLinkListView.as_view(), name="friend-links"),
    path("site-config/", views.SiteConfigView.as_view(), name="site-config"),
    # Admin API
    path("admin/", include(admin_router.urls)),
    path("admin/site-config/", views_admin.AdminSiteConfigView.as_view(), name="admin-site-config"),
    path("admin/upload/", views_admin.ImageUploadView.as_view(), name="admin-upload"),
    path("admin/dashboard/", views_admin.DashboardView.as_view(), name="admin-dashboard"),
]
