from django.conf import settings


def additional_context(request):
    return {"DATA_SUBMISSION_ENABLED": settings.DATA_SUBMISSION_ENABLED}
