from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from task_service_backend import views
from rest_framework.routers import DefaultRouter
from django.urls import re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.contrib.auth import views as auth_views


schema_view = get_schema_view(
   openapi.Info(
      title="Task Service API",
      default_version='v1',
      description="A Task Assignment Service",
    #   terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="bingzhen.jiang@outlook.com"),
    #   license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'properties', views.PropertyViewSet, basename='property')
router.register(r'task_properties', views.TaskPropertyViewSet, basename='task_property')
router.register(r'user_properties', views.UserPropertyViewSet, basename='user_property')
router.register(r'user_profiles', views.UserProfileViewSet, basename='user_profile')
router.register(r'user_behaviors', views.UserBehaviorViewSet, basename='user_behavior')

urlpatterns = router.urls
# urlpatterns = format_suffix_patterns(urlpatterns)

urlpatterns = [
   path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
   path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
   path('', include(router.urls)),
   # # path('admin/', admin.site.urls),
   # path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
]
