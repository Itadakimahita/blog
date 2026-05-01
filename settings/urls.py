# Python modules
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
from apps.users.token_views import DocumentedTokenRefreshView, DocumentedTokenVerifyView
from apps.abstracts.views import StatsAPIView
from apps.core.views import AuthLanguageAPIView, AuthTimezoneAPIView
from apps.notifications.views import post_publication_stream

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path(route="api/users/", view=include("apps.users.urls")),
    # Blog endpoints (canonical)
    # path(route="api/tasks/", view=include("apps.tasks.urls")),
    # path(route="api/auths/", view=include("apps.auths.urls")),
    
    path('api/token/', RateLimitedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', DocumentedTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', DocumentedTokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/token/', RateLimitedTokenObtainPairView.as_view(), name='auth_token_obtain_pair'),
    path('api/auth/register/', UserViewSet.as_view({'post': 'register'}), name='auth_register'),
    path('api/auth/language/', AuthLanguageAPIView.as_view(), name='auth_language'),
    path('api/auth/timezone/', AuthTimezoneAPIView.as_view(), name='auth_timezone'),
    path('api/posts/', PostViewSet.as_view({'get': 'get_posts', 'post': 'create_post'}), name='posts_list_create'),
    path('api/posts/stream/', post_publication_stream, name='posts-stream'),
    path(
        'api/posts/<slug:slug>/',
        PostViewSet.as_view({'get': 'get_post', 'patch': 'update_post', 'delete': 'delete_post'}),
        name='posts_detail_update_delete',
    ),
    path(
        'api/posts/<slug:slug>/comments/',
        PostViewSet.as_view({'get': 'get_post_comments', 'post': 'create_post_comment'}),
        name='posts_comments_list_create',
    ),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/stats/', StatsAPIView.as_view(), name='stats'),
    
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
] + debug_toolbar_urls()

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
