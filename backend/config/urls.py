from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin-django/", admin.site.urls),
    path("api/", include("apps.blog.urls")),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.quant.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar
    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
