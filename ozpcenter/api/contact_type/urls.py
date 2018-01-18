"""
Contact Types URLs
"""
from django.conf.urls import url, include
from rest_framework import routers

import ozpcenter.api.contact_type.views as views

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()

router.register(r'contact_type', views.ContactTypeViewSet)
router.register(r'contact', views.ContactViewSet)

# Wire up our API using automatic URL routing.
urlpatterns = [
    url(r'^', include(router.urls)),
]
