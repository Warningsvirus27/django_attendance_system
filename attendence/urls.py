from django.contrib import admin
from django.urls import path, include

# needed for hosting on heroku
import settings
from django.views.static import serve
from django.conf.urls import url


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('page.urls')),
    path('', include('django.contrib.auth.urls')),

    # needed for hosting on heroku
    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

