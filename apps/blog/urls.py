# Django modules
from django.urls import include, path

# Django Rest Framework modules
from rest_framework.routers import DefaultRouter

# Project modules
from apps.blog.views import PostViewSet


router: DefaultRouter = DefaultRouter(
    trailing_slash=False
)

router.register(
    prefix="posts",
    viewset=PostViewSet,
    basename="post",
)

urlpatterns = [
    path("v1/", include(router.urls)),
]