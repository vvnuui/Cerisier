from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"posts", views.PostViewSet, basename="post")

urlpatterns = [
    path("", include(router.urls)),
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("tags/", views.TagListView.as_view(), name="tag-list"),
    path("archives/", views.ArchiveView.as_view(), name="archive-list"),
]
