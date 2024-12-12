from cove.html_error_msg import html_error_msg
from cove.templatetags.cove_tags import register
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _
from cove.templatetags.cove_tags import cove_modal_errors, cove_modal_list


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
    elif error["error_id"] == "oneOf_each_required":
        return mark_safe(_(
            f"Only 1 of <code>{error['extras'][0]}</code> or <code>{error['extras'][1]}</code> is permitted, but both are present"
        ))

    return html_error_msg(error)


# wrap lib-cove-web implementation to provide our own template
@register.inclusion_tag("cove_360/modal_errors.html")
def cove_360_modal_errors(**context):
    return cove_modal_errors(**context)


# wrap lib-cove-web implementation to provide our own template
@register.inclusion_tag("cove_360/modal_list.html")
def cove_360_modal_list(**context):
    return cove_modal_list(**context)


@register.filter("multiply")
def multiply(a, b):
    return a*b
