import codecs
import csv
import itertools
import json
import logging
from decimal import Decimal

from cove.views import explore_data_context, cove_web_input_error
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from libcove.config import LibCoveConfig
from libcove.lib.converters import convert_spreadsheet, convert_json
from libcove.lib.exceptions import CoveInputDataError

from lib360dataquality.cove.schema import Schema360
from lib360dataquality.cove.threesixtygiving import TEST_CLASSES
from lib360dataquality.cove.threesixtygiving import common_checks_360

logger = logging.getLogger(__name__)


@cove_web_input_error
def explore_360(request, pk, template='cove_360/explore.html'):
    schema_360 = Schema360()
    context, db_data, error = explore_data_context(request, pk)
    if error:
        return error

    lib_cove_config = LibCoveConfig()
    lib_cove_config.config.update(settings.COVE_CONFIG)

    upload_dir = db_data.upload_dir()
    upload_url = db_data.upload_url()
    file_name = db_data.original_file.file.name
    file_type = context['file_type']

    if file_type == 'json':
        # open the data first so we can inspect for record package
        with open(file_name, encoding='utf-8') as fp:
            try:
                json_data = json.load(fp, parse_float=Decimal)
            except ValueError as err:
                raise CoveInputDataError(context={
                    'sub_title': _("Sorry, we can't process that data"),
                    'link': 'index',
                    'link_text': _('Try Again'),
                    'msg': _(format_html('We think you tried to upload a JSON file, but it is not well formed JSON.'
                             '\n\n<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true">'
                             '</span> <strong>Error message:</strong> {}', err)),
                    'error': format(err)
                })
            if not isinstance(json_data, dict):
                raise CoveInputDataError(context={
                    'sub_title': _("Sorry, we can't process that data"),
                    'link': 'index',
                    'link_text': _('Try Again'),
                    'msg': _('360Giving JSON should have an object as the top level, the JSON you supplied does not.'),
                })

            context.update(convert_json(upload_dir, upload_url, file_name, schema_url=schema_360.schema_url,
                                        request=request, flatten=request.POST.get('flatten'),
                                        lib_cove_config=lib_cove_config))

    else:
        def conversion_warning_hook(w):
            if hasattr(w.message, "path_till_now"):
                if w.message.path_till_now == "publisher":
                    return 'Just "Publisher" should not appear in the Meta tab, did you mean "Publisher:Name"?'
            else:
                return w

        context.update(convert_spreadsheet(upload_dir, upload_url, file_name, file_type, lib_cove_config, schema_360.schema_url,
                                           schema_360.pkg_schema_url, conversion_warning_hook=conversion_warning_hook))
        with open(context['converted_path'], encoding='utf-8') as fp:
            json_data = json.load(fp, parse_float=Decimal)

    context = common_checks_360(context, upload_dir, json_data, schema_360)

    if hasattr(json_data, 'get') and hasattr(json_data.get('grants'), '__iter__'):
        context['grants'] = json_data['grants']

        context['metadata'] = {}
        for key, value in json_data.items():
            if key != 'grants':
                if isinstance(value, dict):
                    value = {k.lower(): v for k, v in value.items()}
                context['metadata'][key.lower()] = value
    else:
        context['grants'] = []
        context['metadata'] = {}

    context['first_render'] = not db_data.rendered
    if not db_data.rendered:
        db_data.rendered = True
    db_data.save()

    return render(request, template, context)


def common_errors(request):
    return render(request, 'cove_360/common_errors.html')


def additional_checks(request):
    context = {}

    test_classes = list(itertools.chain(*TEST_CLASSES.values()))
    context['checks'] = [
        {
            'heading': check.check_text['heading'],
            'messages': (check.check_text['message'].ordered_dict.items()),
            'desc': check.__doc__,
            'class_name': check.__name__
        } for check in test_classes
    ]

    if request.path.endswith('.csv'):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="additional_checks.csv"'

        response.write(codecs.BOM_UTF8)

        writer = csv.writer(response)
        writer.writerow(['Class Name', 'Methodology', 'Heading', '%', 'Message'])
        for check in context['checks']:
            for message in check['messages']:
                writer.writerow([check['class_name'], check['desc'], check['heading'], message[0], message[1]])

        return response

    else:
        return render(request, 'cove_360/additional_checks.html', context)
