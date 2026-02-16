# Django modules
from django.urls import include, path

# Django Rest Framework modules
from rest_framework.routers import DefaultRouter

# Project modules
from apps.users.views import UserViewSet


router: DefaultRouter = DefaultRouter(
    trailing_slash=False
)

router.register(
    prefix="users",
    viewset=UserViewSet,
    basename="user",
)

urlpatterns = [
    path("v1/", include(router.urls)),
]