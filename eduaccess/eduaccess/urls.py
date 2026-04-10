"""
URL configuration for eduaccess project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from whatsapp_bot.views import (
    EduAccessLoginView,
    EduAccessLogoutView,
    audio_pack_player,
    audio_pack_transcript_download,
    dashboard_page,
    landing_page,
    learning_pack_download,
    offline_fallback_page,
    offline_library_page,
    pwa_manifest,
    register_page,
    service_worker,
    study_assistant_api,
    study_assistant_page,
    welcome_page,
    whatsapp_webhook,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='home'),
    path('register/', register_page, name='register'),
    path('welcome/', welcome_page, name='welcome'),
    path('login/', EduAccessLoginView.as_view(), name='login'),
    path('logout/', EduAccessLogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard_page, name='dashboard'),
    path('manifest.json', pwa_manifest, name='manifest'),
    path('service-worker.js', service_worker, name='service_worker'),
    path('study-assistant/', study_assistant_page, name='study_assistant'),
    path('study-assistant/api/', study_assistant_api),
    path('offline-fallback/', offline_fallback_page, name='offline_fallback'),
    path('offline-library/', offline_library_page, name='offline_library'),
    path('packs/<slug:slug>/', learning_pack_download),
    path('audio-packs/<slug:slug>/player/', audio_pack_player),
    path('audio-packs/<slug:slug>/transcript/', audio_pack_transcript_download),
    path('whatsapp/', whatsapp_webhook),
]
