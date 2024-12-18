from django.conf import settings


def additional_context(request):
    return {
        "DATA_SUBMISSION_ENABLED": settings.DATA_SUBMISSION_ENABLED,
        "DEBUG": settings.DEBUG,
        "DISABLE_COOKIE_POPUP": settings.DISABLE_COOKIE_POPUP,
    }
