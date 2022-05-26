from django.core.serializers import serialize
from django.views import View
from django.http import JsonResponse
from cove.input.models import SuppliedData
from django.shortcuts import get_object_or_404


class ResultsApiView(View):
	def get(self, *args, **kwargs):
		results = get_object_or_404(SuppliedData, id=kwargs["id"])
		return JsonResponse(results)
