from cove.html_error_msg import html_error_msg
from cove.templatetags.cove_tags import register
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _


@register.filter(name='html_error_msg')
def html_error_msg_360(error):
    """
    Replaces default `html_error_msg` and then chains up with the implementation of lib-cove-web.
    """
    if error["error_id"] == "uniqueItems_with_id":
        return mark_safe(_(
            "Non-unique id values. There are grants in your data with the same Id. "
            "Each Id must be unique so the grants can be distinguished from each other. "
            "If there are duplicate grant records in your data these should be removed. "
            "If different grants have the same Id these should be updated to make them unique. "
            "<a href=\"https://standard.threesixtygiving.org/en/latest/identifiers/#grant-identifier\" target=\"_blank\">(more info)</a>"
        ))

    return html_error_msg(error)
