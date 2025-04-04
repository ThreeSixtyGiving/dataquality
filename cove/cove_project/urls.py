from django.conf.urls.static import static
from django.conf import settings
from django.urls import path
from django.views.generic import TemplateView

from cove.urls import urlpatterns, handler500  # noqa: F401

import cove_360.views
import cove_360.api

urlpatterns += [
    path("results/<uuid:pk>/advanced", cove_360.views.explore_360, name='results', kwargs=dict(template='cove_360/explore_advanced.html')),
    path("results/<uuid:pk>", cove_360.views.explore_360, name='results'),
    path("data/<uuid:pk>", cove_360.views.data_loading, name='explore'),
    path("api/results/<uuid:pk>", cove_360.api.ResultsApiView.as_view(), name="api-results"),
    path("xhr_results_ready/<uuid:pk>", cove_360.views.results_ready, name='xhr_results_ready'),
    path("common_errors", cove_360.views.common_errors, name='common_errors'),
    path("additional_checks", cove_360.views.additional_checks, name='additional_checks'),
    path("submit", TemplateView.as_view(template_name="cove_360/publishing.html", extra_context={"submission_tool": True}), name="publishing"),
    path("terms-conditions", TemplateView.as_view(template_name="cove_360/terms.html"), name="terms-conditions"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
