# Python modules
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from debug_toolbar.toolbar import debug_toolbar_urls

# Django modules
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Project modules
from apps.users.urls import urlpatterns as users_urlpatterns
from apps.users.views import UserViewSet
from apps.blog.views import PostViewSet
from apps.users.auth_views import RateLimitedTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path(route="api/users/", view=include("apps.users.urls")),
    path(route="api/blog/", view=include("apps.blog.urls")),
    # path(route="api/tasks/", view=include("apps.tasks.urls")),
    # path(route="api/auths/", view=include("apps.auths.urls")),
    
    path('api/token/', RateLimitedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/token/', RateLimitedTokenObtainPairView.as_view(), name='auth_token_obtain_pair'),
    path('api/auth/register/', UserViewSet.as_view({'post': 'register'}), name='auth_register'),
    path('api/posts/', PostViewSet.as_view({'get': 'get_posts', 'post': 'create_post'}), name='posts_list_create'),
    
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
] + debug_toolbar_urls()

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
