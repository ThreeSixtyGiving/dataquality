from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from cove_360.models import SuppliedDataStatus


class ResultsApiView(View):
    def get(self, *args, **kwargs):
        results = get_object_or_404(SuppliedDataStatus, supplied_data=kwargs["id"])

        return JsonResponse(
            {
                "id": results.supplied_data.id,
                "file": str(results.supplied_data.original_file).split("/")[1:][0],
                "url": results.supplied_data.source_url,
                "created": results.supplied_data.created,
                "passed": results.passed,
                "can_publish": results.can_publish,
                "publisher": results.publisher
            }
        )
