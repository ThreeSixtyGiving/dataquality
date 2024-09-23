from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings
from django.urls import path
from django.views.generic import TemplateView

from cove.urls import urlpatterns, handler500  # noqa: F401

import cove_360.views
import cove_360.api

urlpatterns += [
    url(r'^results/(.+)/advanced$', cove_360.views.explore_360, name='results', kwargs=dict(template='cove_360/explore_advanced.html')),
    url(r'^results/(.+)$', cove_360.views.explore_360, name='results'),
    url(r'^data/(.+)$', cove_360.views.data_loading, name='explore'),
    path("api/results/<uuid:id>", cove_360.api.ResultsApiView.as_view(), name="api-results"),
    url(r'^xhr_results_ready/(.+)$', cove_360.views.results_ready, name='xhr_results_ready'),
    url(r'^common_errors', cove_360.views.common_errors, name='common_errors'),
    url(r'^additional_checks', cove_360.views.additional_checks, name='additional_checks'),
    path("publishing/", TemplateView.as_view(template_name="cove_360/publishing.html"), name="publishing"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
