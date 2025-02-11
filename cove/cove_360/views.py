import codecs
import csv
import itertools
import json
import logging
import re
import os
from decimal import Decimal

from cove.views import explore_data_context, cove_web_input_error
from cove.input.models import SuppliedData

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

from libcove.config import LibCoveConfig
from libcove.lib.converters import convert_spreadsheet, convert_json
from libcove.lib.exceptions import CoveInputDataError

from lib360dataquality.cove.schema import Schema360, ExtensionsError
from lib360dataquality.cove.threesixtygiving import TEST_CLASSES, TestType
from lib360dataquality.cove.threesixtygiving import common_checks_360

from cove_360.models import SuppliedDataStatus
from cove_360.publishing import lookup_publisher_by_domain, extract_domain

logger = logging.getLogger(__name__)


def results_ready(request, pk):
    try:
        data = SuppliedData.objects.get(pk=pk)
    except SuppliedData.DoesNotExist:
        return JsonResponse({"done": False})

    return JsonResponse({"done": data.rendered})


def data_loading(request, pk, template='cove_360/data_loading.html'):
    # Backward compatibility if we receive a post request to the loading page
    if request.method == 'POST':
        return explore_360(request, pk)

    # Data already loaded so redirect to results page
    try:
        if SuppliedData.objects.get(pk=pk).rendered is True:
            redirect('results', pk)
    except SuppliedData.DoesNotExist:
        pass

    return render(request, template, {"pk": pk})


@cove_web_input_error
def explore_360(request, pk, template='cove_360/explore.html'):

    cached_context = cache.get(pk)

    if cached_context and not request.POST.get("flatten"):

        if request.GET.get("new-mode"):
            # We're swapping into DQT mode from submission, to avoid having
            # to re-run the checks we reset/remove the submission context data
            # which then causes the explore template to swap back to the DQT.
            try:
                db_data = SuppliedData.objects.get(pk=pk)
                data_params = json.loads(db_data.parameters)
                del data_params["self_publishing"]
                db_data.parameters = json.dumps(data_params)
                db_data.save()
                data_status, dsc = SuppliedDataStatus.objects.get_or_create(
                    supplied_data=db_data,
                )
                cached_context["data_status"] = data_status
                cached_context["submission_tool"] = False
                cache.set(pk, cached_context)
            except KeyError:
                pass

        print("Cache hit")
        return render(request, template, cached_context)

    context, db_data, error = explore_data_context(request, pk)
    if error:
        return error

    data_status, dsc = SuppliedDataStatus.objects.get_or_create(
        supplied_data=db_data,
    )
    context["data_status"] = data_status
    if db_data.source_url:
        context["source_url_domain"] = extract_domain(db_data.source_url)

    if db_data.parameters and "self_publishing" in db_data.parameters:
        publisher = lookup_publisher_by_domain(db_data.source_url)
        if not publisher:
            # We're trying to self publish but we can't find any matching publisher
            # bail out early so user doesn't have to wait for validation to complete
            return render(request, "cove_360/publisher_not_found.html", context)
        data_status._publisher = json.dumps(publisher)
        context["submission_tool"] = True
        context["publisher"] = publisher

    lib_cove_config = LibCoveConfig()
    lib_cove_config.config.update(settings.COVE_CONFIG)

    upload_dir = db_data.upload_dir()
    upload_url = db_data.upload_url()
    file_name = db_data.original_file.file.name
    file_type = context['file_type']
    schema_360 = Schema360(upload_dir)

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

            extension_metadatas = schema_360.resolve_extension(json_data)

            context.update(convert_json(upload_dir, upload_url, file_name, schema_url=schema_360.schema_file,
                                    request=request, flatten=request.POST.get('flatten'),
                                    lib_cove_config=lib_cove_config))

    else:
        # Convert spreadsheet to json
        context.update(convert_spreadsheet(upload_dir, upload_url, file_name, file_type, lib_cove_config, schema_360.schema_file,
                                           schema_360.pkg_schema_file))

        with open(context['converted_path'], encoding='utf-8') as fp:
            json_data = json.load(fp, parse_float=Decimal)

        try:
            # Check data for presence of any schema extensions if exists re-convert using the newly patched schema
            if extension_metadatas := schema_360.resolve_extension(json_data):
                # Delete old converted data. If it is detected by libcove it will skip conversion (unflattening)
                os.unlink(context["converted_path"])

                context.update(convert_spreadsheet(upload_dir, upload_url, file_name, file_type, lib_cove_config, schema_360.schema_file, schema_360.pkg_schema_file))
                # Re-load the newly flattened data
                with open(context['converted_path'], encoding='utf-8') as fp:
                    json_data = json.load(fp, parse_float=Decimal)

                context["extension_metadatas"] = extension_metadatas
        except ExtensionsError as err:
            raise CoveInputDataError(context={
                    'sub_title': _("Sorry, we can't process the data with the specified extension(s)"),
                    'link': 'index',
                    'link_text': _('Try Again'),
                    'msg': _(format_html('We think you tried to upload data that uses an extension to the 360Giving standard. However there was a problem with the extension.'
                             '\n\n<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true">'
                             '</span> <strong>Error message:</strong> {}', err)),
                    'error': format(err)
                })

    context = common_checks_360(context, upload_dir, json_data, schema_360)

    # Construct the 360Giving specific urls for codelists in the docs
    for key in ['additional_closed_codelist_values', 'additional_open_codelist_values']:
        for path_string, codelist_info in context[key].items():
            codelist_info['codelist_url'] = (
                'https://standard.threesixtygiving.org/en/latest/technical/codelists/#' +
                re.sub(r'([A-Z])', r'-\1', codelist_info['codelist'].split('.')[0]).lower()
            )

    if settings.GRANTS_TABLE and hasattr(json_data, 'get') and hasattr(json_data.get('grants'), '__iter__'):
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
        context["json_data"] = {}

    context['first_render'] = not db_data.rendered
    if not db_data.rendered:
        db_data.rendered = True

    db_data.save()

    data_status.passed = context['validation_errors_count'] == 0
    data_status.save()

    try:
        context["usefulness_categories"] = set([message["category"] for message, a, b in context["usefulness_checks"]])
    except TypeError:
        # if no usefulness_checks the iteration will fail
        context["usefulness_categories"] = []

    try:
        context["quality_accuracy_categories"] = set([message["category"] for message, a, b in context["quality_accuracy_checks"]])
    except TypeError:
        # if no quality quality_accuracy categories the iteration will fail
        context["quality_accuracy_categories"] = []

    # TODO: Check if this is needed any more
    #  try:
    #      context["quality_accuracy_checks_passed"] = create_passed_tests_context_data(context["quality_accuracy_checks"], TEST_CLASSES["quality_accuracy"])
    #   except Exception:
    #      context["quality_accuracy_errored"] = True
    #    try:
    #       context["usefulness_checks_passed"] = create_passed_tests_context_data(context["usefulness_checks"], TEST_CLASSES["usefulness"])
    #  except Exception:
    #     context["usefulness_errored"] = True

    context["total_quality_accuracy_checks"] = len(TEST_CLASSES[TestType.QUALITY_TEST_CLASS])
    context["total_usefulness_checks"] = len(TEST_CLASSES[TestType.USEFULNESS_TEST_CLASS])

    # Sort accuracy using the importance field
    if context["quality_accuracy_checks"]:
        context["quality_accuracy_checks"].sort(key=lambda x: x[0]["importance"], reverse=True)

    if settings.DEBUG:
        cache.clear()
    else:
        cache.set(pk, context)

    # Helpful when debugging DQT
    # import pprint
    # pprint.pprint(context, stream=open("/tmp/dqt.py", "w"), indent=2)
    return render(request, template, context)


def create_passed_tests_context_data(failed_tests, available_tests):
    """ Creates a list of test that have passed """

    passed_tests_names = [test[0]["type"] for test in failed_tests]
    passed_test_case_headings = []

    for test in available_tests:
        if test.__name__ in passed_tests_names:
            continue
        # We instantiate the test with no data to be able to utilise the heading formatting code
        # TODO this may no longer be needed
        # passed_test_case = test(grants=[], aggregates={"count": 0, "recipient_individuals_count": 0})
        # passed_test_case_headings.append(mark_safe(passed_test_case.format_heading_count(test.check_text["heading"])))
        passed_test_case_headings.append(test.__name__)

    return passed_test_case_headings


def common_errors(request):
    return render(request, 'cove_360/common_errors.html')


def additional_checks(request):
    context = {}
    check_types = []

    for check_type in vars(TestType):
        if check_type.startswith("_"):
            continue

        test_check_cat_name = getattr(TestType, check_type)

        test_classes = list(itertools.chain(TEST_CLASSES[test_check_cat_name]))

        check_types.append(test_check_cat_name)

        context[f"checks_{test_check_cat_name}"] = [
                {
                    'heading': check.check_text['heading'],
                    'messages': (check.check_text['message'].ordered_dict.items()),
                    'desc': check.__doc__,
                    'class_name': check.__name__,
                } for check in test_classes
            ]

    if request.path.endswith('.csv'):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="additional_checks.csv"'

        response.write(codecs.BOM_UTF8)

        writer = csv.writer(response)
        writer.writerow(['Class Name', 'Methodology', 'Heading', '%', 'Message'])
        for check_type in check_types:
            for check in context[f"checks_{check_type}"]:
                for message in check['messages']:
                    writer.writerow([check['class_name'], check['desc'], check['heading'], message[0], message[1]])

        return response

    else:
        return render(request, 'cove_360/additional_checks.html', context)
