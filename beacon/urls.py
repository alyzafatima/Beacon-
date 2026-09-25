from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView , LogoutView

from rest_framework.routers import DefaultRouter
from monitoring.views import *




router = DefaultRouter()
router.register(r'monitors', MonitorViewSet, basename='monitor')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(), name='login'),
    path('api/', include(router.urls)),
    path('ping/<str:token>/', heartbeat_ping, name='heartbeat-ping'),
    path(
    'signup/',
    signup,
    name='signup'
),
path(
    'dashboard/',
    dashboard,
    name='dashboard'
),
path(
    'logout/',
    LogoutView.as_view(),
    name='logout'
),
path(
    'monitor/<int:monitor_id>/',
    monitor_detail,
    name='monitor-detail'
),
path(
    'monitor/add/',
    add_monitor,
    name='add-monitor'
),
path(
    'alerts/',
    alerts_settings,
    name='alerts-settings'
),
path(
    'status/<slug:slug>/',
    public_status_page,
    name='public-status-page'
),
path('status-pages/', status_pages, name='status-pages'),
path("", landing, name="landing"),

path(
    "account/",
    account_billing,
    name="account-billing"
),
]