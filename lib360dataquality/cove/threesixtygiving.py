import datetime
import functools
import itertools
import json
import re
from collections import OrderedDict, defaultdict
from decimal import Decimal

import libcove.lib.tools as tools
import openpyxl
import pytz
from dateutil.relativedelta import relativedelta
from jsonschema.exceptions import ValidationError
from libcove.lib.common import common_checks_context, get_additional_codelist_values, get_orgids_prefixes, validator
from libcove.lib.tools import decimal_default
from rangedict import RangeDict as range_dict

try:
    from django.utils.html import mark_safe
except ImportError:
    # If we don't have django we're not using this lib in CoVE so we're not using the output
    # in HTML and therefore do not need a SafeString object.
    def mark_safe(string):
        return string

QUALITY_TEST_CLASS = "quality_accuracy"
USEFULNESS_TEST_CLASS = "usefulness"

DATES_JSON_LOCATION = {
    "award_date": "/awardDate",
    "planned_start_date": "/plannedDates/0/startDate",
    "planned_end_date": "/plannedDates/0/endDate",
    "actual_start_date": "/actualDates/0/startDate",
    "actual_end_date": "/actualDates/0/endDate",
}

orgids_prefixes = get_orgids_prefixes()
orgids_prefixes.append("360G")

currency_html = {"GBP": "&pound;", "USD": "$", "EUR": "&euro;"}


class RangeDict(range_dict):
    """
    Override RangeDict library to work as an OrderedDict.
    """

    def __init__(self):
        super(RangeDict, self).__init__()
        self.ordered_dict = OrderedDict()

    def __setitem__(self, r, v):
        super(RangeDict, self).__setitem__(r, v)
        self.ordered_dict[r] = v


def oneOf_draft4(validator, oneOf, instance, schema):
    """
    oneOf_draft4 validator based on
    https://github.com/open-contracting/lib-cove-ocds/blob/2fbaffe95c7c9e7b78aaebcac492e402be08c0b5/libcoveocds/common_checks.py#L40-L115
    originally from
    https://github.com/Julian/jsonschema/blob/d16713a4296663f3d62c50b9f9a2893cb380b7af/jsonschema/_validators.py#L337
    Modified to:
    - Yield individual errors, by picking the appropriate subschema. This is
      hard wired, so only works for recipientIndividual/recipientOrganization.
      If more oneOf's are added, this code must be changed.
    - sort the instance JSON, so we get a reproducible output that we
      can can test more easily
    - Return more information on the ValidationError object, to allow us to
      replace the translation with a message in cove-ocds
    """
    # We check the title, because we don't have access to the field name,
    # as it lives in the parent.
    #
    # This section produces a message for the specific case where a oneOf is
    # just a difference between 2 required fields. This happens at the top of
    # this function, so that we get a message when neither subschema validates
    # (ordinarily we would not)
    if (
        schema.get("title") == "360Giving Data Standard Schema" and
        len(oneOf) == 2
        and set(oneOf[0].keys()) == set(oneOf[1].keys()) == {"required"}
    ):
        required_fields_1 = set(oneOf[0]["required"]) - set(oneOf[1]["required"])
        required_fields_2 = set(oneOf[1]["required"]) - set(oneOf[0]["required"])
        if len(required_fields_1) == 1 and len(required_fields_2) == 1:
            required_field_1 = list(required_fields_1)[0]
            required_field_2 = list(required_fields_2)[0]
            if type(instance) is dict and required_field_1 in instance and required_field_2 in instance:
                err = ValidationError(f"Only 1 of {required_field_1} or {required_field_2} is permitted, but both are present")
                err.error_id = "oneOf_each_required"
                err.extras = [required_field_1, required_field_2]
                yield err

    subschemas = enumerate(oneOf)
    all_errors = []
    for index, subschema in subschemas:
        errs = list(validator.descend(instance, subschema, schema_path=index))
        if not errs:
            first_valid = subschema
            break
        # We check the title, because we don't have access to the field name,
        # as it lives in the parent.
        if (
            schema.get("title") == "360Giving Data Standard Schema"
        ):
            # If the instance has a `recipientIndividual` key, use the
            # subschema that requires that, otherwise use the subschema that
            # requires `recipientOrganization`
            if type(instance) is dict and "recipientIndividual" in instance:
                if "recipientIndividual" in subschema.get("required", []):
                    for err in errs:
                        err.assumption = "recipientIndividual"
                        yield err
                    return
            else:
                if "recipientOrganization" in subschema.get("required", []):
                    for err in errs:
                        err.assumption = "recipientOrganization"
                        yield err
                    return
        all_errors.extend(errs)
    else:
        err = ValidationError(
            f"{json.dumps(instance, sort_keys=True, default=decimal_default)} "
            "is not valid under any of the given schemas",
            context=all_errors,
        )
        err.error_id = "oneOf_any"
        yield err

    more_valid = [s for i, s in subschemas if validator.is_valid(instance, s)]
    if more_valid:
        more_valid.append(first_valid)
        reprs = ", ".join(repr(schema) for schema in more_valid)
        err = ValidationError(f"{instance!r} is valid under each of {reprs}")
        err.error_id = "oneOf_each"
        err.reprs = reprs
        yield err


validator.VALIDATORS["oneOf"] = oneOf_draft4


@tools.ignore_errors
def get_grants_aggregates(json_data):

    id_count = 0
    count = 0
    unique_ids = set()
    duplicate_ids = set()
    max_award_date = ""
    min_award_date = ""
    award_years = {}
    distinct_funding_org_identifier = set()
    distinct_recipient_org_identifier = set()
    currencies = {}
    recipient_individuals_count = 0

    if "grants" in json_data:
        for grant in json_data["grants"]:
            count = count + 1
            currency = grant.get("currency")

            if currency not in currencies.keys():
                currencies[currency] = {
                    "count": 0,
                    "total_amount": 0,
                    "max_amount": 0,
                    "min_amount": 0,
                    "currency_symbol": currency_html.get(currency, ""),
                }

            currencies[currency]["count"] += 1
            amount_awarded = grant.get("amountAwarded")
            if amount_awarded and isinstance(amount_awarded, (int, Decimal, float)):
                currencies[currency]["total_amount"] += amount_awarded
                currencies[currency]["max_amount"] = max(
                    amount_awarded, currencies[currency]["max_amount"]
                )
                if not currencies[currency]["min_amount"]:
                    currencies[currency]["min_amount"] = amount_awarded
                currencies[currency]["min_amount"] = min(
                    amount_awarded, currencies[currency]["min_amount"]
                )

            award_date = str(grant.get("awardDate", ""))
            if award_date:
                try:
                    year = award_date[:4]
                    # count up the tally of grants in `year`
                    award_years[year] = award_years[year] + 1
                except KeyError:
                    award_years[year] = 1
                max_award_date = max(award_date, max_award_date)
                if not min_award_date:
                    min_award_date = award_date
                min_award_date = min(award_date, min_award_date)

            grant_id = grant.get("id")
            if grant_id:
                id_count = id_count + 1
                if grant_id in unique_ids:
                    duplicate_ids.add(grant_id)
                unique_ids.add(grant_id)

            funding_orgs = grant.get("fundingOrganization", [])
            for funding_org in funding_orgs:
                funding_org_id = funding_org.get("id")
                if funding_org_id:
                    distinct_funding_org_identifier.add(funding_org_id)

            recipient_orgs = grant.get("recipientOrganization", [])
            for recipient_org in recipient_orgs:
                recipient_org_id = recipient_org.get("id")
                if recipient_org_id:
                    distinct_recipient_org_identifier.add(recipient_org_id)

            if grant.get("recipientIndividual", None):
                recipient_individuals_count += 1

    recipient_org_prefixes = get_prefixes(distinct_recipient_org_identifier)
    recipient_org_identifier_prefixes = recipient_org_prefixes["prefixes"]
    recipient_org_identifiers_unrecognised_prefixes = recipient_org_prefixes[
        "unrecognised_prefixes"
    ]

    funding_org_prefixes = get_prefixes(distinct_funding_org_identifier)
    funding_org_identifier_prefixes = funding_org_prefixes["prefixes"]
    funding_org_identifiers_unrecognised_prefixes = funding_org_prefixes[
        "unrecognised_prefixes"
    ]

    return {
        "count": count,
        "id_count": id_count,
        "unique_ids": unique_ids,
        "duplicate_ids": duplicate_ids,
        "max_award_date": max_award_date.split("T")[0],
        "min_award_date": min_award_date.split("T")[0],
        "award_years": award_years,
        "distinct_funding_org_identifier": distinct_funding_org_identifier,
        "distinct_recipient_org_identifier": distinct_recipient_org_identifier,
        "recipient_individuals_count": recipient_individuals_count,
        "currencies": currencies,
        "recipient_org_identifier_prefixes": recipient_org_identifier_prefixes,
        "recipient_org_identifiers_unrecognised_prefixes": recipient_org_identifiers_unrecognised_prefixes,
        "funding_org_identifier_prefixes": funding_org_identifier_prefixes,
        "funding_org_identifiers_unrecognised_prefixes": funding_org_identifiers_unrecognised_prefixes,
    }


def group_validation_errors(validation_errors, file_type, openpyxl_workbook):
    validation_errors_grouped = defaultdict(list)
    for error_json, values in validation_errors:
        error = json.loads(error_json)
        error_extra = {
            "values": values,
            "spreadsheet_style_errors_table": spreadsheet_style_errors_table(
                values, openpyxl_workbook
            )
            if (file_type in ["xlsx", "csv"] and "grants/" in error["path_no_number"])
            else None,
        }
        if error["validator"] == "required":
            validation_errors_grouped["required"].append((error_json, error_extra))
        elif error["validator"] == "format" or (error["validator"] == "oneOf" and "format" in error["validator_value"][0]):
            validation_errors_grouped["format"].append((error_json, error_extra))
        else:
            validation_errors_grouped["other"].append((error_json, error_extra))
    return validation_errors_grouped


def extend_numbers(numbers):
    """
    Add the previous/next number for each number, if it doesn't
    already exist in the list (or is 0).
    e.g. list(extend_numbers([4, 5, 7, 2001])) == [3, 4, 5, 6, 7, 8, 2000, 2001, 2002]

    """
    prev_numbers, numbers, next_numbers = itertools.tee(numbers, 3)
    prev_numbers = itertools.chain([-1], prev_numbers)
    next(next_numbers)
    for number in numbers:
        prev_number = next(prev_numbers, -1)
        next_number = next(next_numbers, None)
        if (
            prev_number != number - 1
            and prev_number + 1 != number - 1
            and number - 1 > 0
        ):
            yield number - 1
        yield number
        if next_number != number + 1:
            yield number + 1


def spreadsheet_style_errors_table(examples, openpyxl_workbook):
    first_few_examples = examples[:3]

    sheets = sorted(set(example.get("sheet") for example in first_few_examples))

    out = {}

    example_cell_lookup = defaultdict(lambda: defaultdict(dict))

    def get_cell(sheet, col_alpha, row_number):
        example_value = (
            example_cell_lookup.get(sheet, {}).get(col_alpha, {}).get(row_number)
        )
        if example_value is not None:
            return {"type": "example", "value": example_value}
        else:
            try:
                value = openpyxl_workbook[sheet][
                    "{}{}".format(col_alpha, row_number)
                ].value
            except (KeyError, AttributeError, TypeError):
                value = ""
            if value is None:
                value = ""
            elif isinstance(value, datetime.datetime):
                value = pytz.timezone("UTC").localize(value).isoformat()
            return {"type": "context", "value": value}

    for sheet in sheets:
        row_numbers = sorted(
            set(
                example["row_number"]
                for example in first_few_examples
                if example.get("sheet") == sheet and "row_number" in example
            )
        )
        col_alphas = sorted(
            set(
                example.get("col_alpha", "???")
                for example in first_few_examples
                if example.get("sheet") == sheet
            )
        )
        if openpyxl_workbook and "???" not in col_alphas:
            row_numbers = list(extend_numbers(row_numbers))
            col_alphas = list(
                map(
                    openpyxl.utils.cell.get_column_letter,
                    extend_numbers(
                        map(openpyxl.utils.cell.column_index_from_string, col_alphas)
                    ),
                )
            )
            if row_numbers and row_numbers[0] != 1:
                row_numbers = [1] + row_numbers
        # Loop through all of the examples, so we don't display an invalid
        # context cell as valid
        for example in examples:
            if (
                example.get("sheet") == sheet
                and example.get("row_number") in row_numbers
                and example.get("col_alpha", "???") in col_alphas
            ):
                example_cell_lookup[example.get("sheet")][
                    example.get("col_alpha", "???")
                ][example.get("row_number")] = example.get("value", "")
        out[sheet] = [[""] + col_alphas] + [
            [row_number]
            + [get_cell(sheet, col_alpha, row_number) for col_alpha in col_alphas]
            for row_number in row_numbers
        ]
    return out


def common_checks_360(
    context,
    upload_dir,
    json_data,
    schema_obj,
    test_classes=None,
):
    """Data Quality Checks for 360Giving packaged data
    context: dictionary to update with results. Must contain "file_type" key.
    upload_dir: directory file exists in if non-json file_type, also used to store validation errors json
    json_data: { grants: [,,] }
    schema_obj: See lib360dataQuality/cove/schema.py for Schema360
    tests: array of test functions to run. Defaults to all available.
    """

    schema_name = schema_obj.pkg_schema_name
    common_checks = common_checks_context(
        upload_dir, json_data, schema_obj, schema_name, context
    )
    cell_source_map = common_checks["cell_source_map"]

    # If no particular test classes are supplied then run all defined here
    if not test_classes:
        test_classes = [QUALITY_TEST_CLASS, USEFULNESS_TEST_CLASS]

    if context["file_type"] == "xlsx":
        try:
            openpyxl_workbook = openpyxl.load_workbook(context["original_file"]["path"])
        # Catch all exceptions here because the same exceptions should
        # be thrown and handled appropriately within flatten-tool.
        except:  # noqa
            openpyxl_workbook = None
    else:
        openpyxl_workbook = None

    context.update(common_checks["context"])
    context.update(
        {
            "grants_aggregates": get_grants_aggregates(json_data, ignore_errors=True),
            "common_error_types": [
                "uri",
                "date-time",
                "required",
                "enum",
                "number",
                "string",
                "minimum",
            ],
            "validation_errors_grouped": group_validation_errors(
                context["validation_errors"], context["file_type"], openpyxl_workbook
            ),
        }
    )

    for test_class_type in test_classes:
        extra_checks = run_extra_checks(
            json_data,
            cell_source_map,
            TEST_CLASSES[test_class_type],
            ignore_errors=True,
            return_on_error=None,
            aggregates=context["grants_aggregates"],
        )

        context.update(
            {
                "{}_errored".format(test_class_type): extra_checks is None,
                "{}_checks".format(test_class_type): extra_checks,
                "{}_checks_count".format(test_class_type): len(extra_checks) if extra_checks else 0
            }
        )

    additional_codelist_values = get_additional_codelist_values(schema_obj, json_data)
    closed_codelist_values = {
        key: value for key, value in additional_codelist_values.items() if not value["isopen"]
    }
    open_codelist_values = {key: value for key, value in additional_codelist_values.items() if value["isopen"]}

    closed_codelist_errors_count = sum(len(value['values']) for value in closed_codelist_values.values())

    context.update(
        {
            "additional_closed_codelist_values": closed_codelist_values,
            "additional_open_codelist_values": open_codelist_values,
            "validation_and_closed_codelist_errors_count": context["validation_errors_count"] + closed_codelist_errors_count
        }
    )

    return context


def get_prefixes(distinct_identifiers):

    org_identifier_prefixes = defaultdict(int)
    org_identifiers_unrecognised_prefixes = defaultdict(int)

    for org_identifier in distinct_identifiers:
        for prefix in orgids_prefixes:
            if org_identifier.startswith(prefix):
                org_identifier_prefixes[prefix] += 1
                break
        else:
            org_identifiers_unrecognised_prefixes[org_identifier] += 1

    return {
        "prefixes": org_identifier_prefixes,
        "unrecognised_prefixes": org_identifiers_unrecognised_prefixes,
    }


def check_charity_number(charity_number):
    charity_number = str(charity_number)
    is_int = True
    try:
        int(charity_number)
    except ValueError:
        is_int = False

    if len(charity_number) in (6, 7) and is_int:
        return True

    return False


company_pattern_re = re.compile("^\w{8}$")


def check_company_number(company_number):
    """Company numbers must be 8 chars long and alpha numeric"""
    return company_pattern_re.match(company_number) is not None


def flatten_dict(grant, path=""):
    for key, value in sorted(grant.items()):
        if isinstance(value, list):
            for num, item in enumerate(value):
                if isinstance(item, dict):
                    yield from flatten_dict(item, "{}/{}/{}".format(path, key, num))
                else:
                    yield ("{}/{}/{}".format(path, key, num), item)
        elif isinstance(value, dict):
            yield from flatten_dict(value, "{}/{}".format(path, key))
        else:
            yield ("{}/{}".format(path, key), value)


RECIPIENT_ANY = ""
RECIPIENT_ORGANISATION = "recipient organisation"
RECIPIENT_INDIVIDUAL = "recipient individual"


class AdditionalTest:
    def __init__(self, **kw):
        self.grants = kw["grants"]
        self.aggregates = kw["aggregates"]
        self.grants_percentage = 0
        self.json_locations = []
        self.failed = False
        self.count = 0
        self.heading = None
        self.message = None
        # Default to the most common type
        self.relevant_grant_type = RECIPIENT_ANY

    def process(self, grant, path_prefix):
        pass

    def produce_message(self):
        return {
            "heading": self.heading,
            "message": self.message,
            "type": self.__class__.__name__,
            "count": self.count,
            "percentage": self.grants_percentage,
        }

    def get_heading_count(self, test_class_type):
        # The total grants is contextual e.g. a test may fail for a recipient org-id
        # this is only relevant to grants to organisations and not individuals
        if self.relevant_grant_type == RECIPIENT_ANY:
            total = self.aggregates["count"]
        elif self.relevant_grant_type == RECIPIENT_ORGANISATION:
            total = self.aggregates["count"] - self.aggregates["recipient_individuals_count"]
        elif self.relevant_grant_type == RECIPIENT_INDIVIDUAL:
            # if there are no individuals in this data then reset the count
            if self.aggregates["recipient_individuals_count"] == 0:
                self.count = 0
            total = self.aggregates["recipient_individuals_count"]

        # Guard against a division by 0
        if total < 1:
            total = 1

        self.grants_percentage = round(self.count / total, 1)
        heading_percentage = "{:.0%}".format(self.grants_percentage)

        # Return conditions

        if test_class_type == QUALITY_TEST_CLASS:
            return self.count

        if self.aggregates["count"] == 1 and self.count == 1:
            self.grants_percentage = 100
            return f"1 {self.relevant_grant_type}".strip()

        if self.grants_percentage < 5:
            return f"{self.count} {self.relevant_grant_type}".strip()

        return f"{heading_percentage} of {self.relevant_grant_type}".strip()

    def format_heading_count(self, message, test_class_type=None, verb="have"):
        """Build a string with count of grants plus message

        The grant count phrase for the test is pluralized and
        prepended to message, eg: 1 grant has + message,
        2 grants have + message or 3 grants contain + message.
        """
        noun = "grant" if self.count == 1 else "grants"
        if verb == "have":
            verb = "has" if self.count == 1 else verb
        elif verb == "do":
            verb = "does" if self.count == 1 else verb
        else:
            # Naively!
            verb = verb + "s" if self.count == 1 else verb
        return "{} {} {} {}".format(
            self.get_heading_count(test_class_type), noun, verb, message
        )


class ZeroAmountTest(AdditionalTest):
    """Check if any grants have an amountAwarded of 0.

    Checks explicitly for a number with a value of 0"""

    check_text = {
        "heading": mark_safe("a value of £0"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "It’s worth taking a look at these grants and deciding if they should be "
        "included in your data. It’s unusual to have grants of £0, but there may be a "
        "reasonable explanation. If £0 value grants are to be published in your data "
        "consider adding an explanation to the description of the grant to help anyone "
        "using the data to understand how to interpret the information."
    )

    def process(self, grant, path_prefix):
        try:
            # check for == 0 explicitly, as other falsey values will be caught
            # by schema validation, and also showing a message about 0 value
            # grants would be more confusing
            if grant["amountAwarded"] == 0:
                self.failed = True
                self.json_locations.append(path_prefix + "/amountAwarded")
                self.count += 1
        except KeyError:
            pass

        self.heading = mark_safe(
            self.format_heading_count(
                self.check_text["heading"], test_class_type=QUALITY_TEST_CLASS
            )
        )
        self.message = self.check_text["message"][self.grants_percentage]


class RecipientOrg360GPrefix(AdditionalTest):
    """Check if any grants are using RecipientOrg IDs that start 360G or 360g"""

    check_text = {
        "heading": mark_safe(
            "a <span class=\"highlight-background-text\">Recipient Org:Identifier</span> that starts '360G-'"
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Use an external reference, such as a charity or company number, to identify an "
        "organisation whenever possible. Doing so makes it possible to see when "
        "recipients have received grants from multiple funders, and allows grants data "
        "to be linked or combined with information from official registers. Some "
        "organisations, such as small unregistered groups, do not have an official "
        "registration number that can be used. In these cases the organisation "
        "identifier should start ‘360G-‘ and use an identifier taken from the "
        "publisher’s internal systems. See our "
        '<a target="_blank" href="https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier">guidance on organisation identifiers</a> '
        "for further help."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_ORGANISATION

    def process(self, grant, path_prefix):
        try:
            for num, organization in enumerate(grant["recipientOrganization"]):
                if organization["id"].lower().startswith("360g"):
                    self.failed = True
                    self.json_locations.append(
                        path_prefix + "/recipientOrganization/{}/id".format(num)
                    )
                    self.count += 1
        except KeyError:
            pass

        self.heading = mark_safe(self.format_heading_count(self.check_text["heading"]))
        self.message = self.check_text["message"][self.grants_percentage]


class FundingOrg360GPrefix(AdditionalTest):
    """Check if any grants are using FundingOrg IDs that start 360G or 360g"""

    check_text = {
        "heading": mark_safe(
            "a <span class=\"highlight-background-text\">Funding Org:Identifier</span> that starts '360G-'"
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Use an external reference, such as a charity or company number, to identify a "
        "funding organisation whenever possible. Some funders do not have an official "
        "registration number that can be used. In these cases the funding organisation "
        "identifier should reuse the publisher prefix and therefore start with “360G-”. See our "
        '<a target="_blank" href="https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier">guidance on organisation identifiers</a> '
        "for further help."
    )

    def process(self, grant, path_prefix):
        try:
            for num, organization in enumerate(grant["fundingOrganization"]):
                if organization["id"].lower().startswith("360g"):
                    self.failed = True
                    self.json_locations.append(
                        path_prefix + "/fundingOrganization/{}/id".format(num)
                    )
                    self.count += 1
        except KeyError:
            pass

        self.heading = mark_safe(self.format_heading_count(self.check_text["heading"]))
        self.message = self.check_text["message"][self.grants_percentage]


class RecipientOrgUnrecognisedPrefix(AdditionalTest):
    """Check if any grants have RecipientOrg IDs that use a prefix that isn't on the Org ID prefix codelist"""

    check_text = {
        "heading": mark_safe(
            'a <span class="highlight-background-text">Recipient Org:Identifier</span> '
            "that does not draw from a recognised register"
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "In the 360Giving Data Standard, organisation identifiers have two parts: an "
        "identifier and a prefix which describes the list the identifier is taken from. "
        "This error notice is caused by the prefix in an organisation identifier not "
        'being taken from a recognised register from the <a target="_blank" href="https://org-id.guide/">org-id list locator</a>. See our '
        '<a target="_blank" href="https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier">guidance on organisation identifiers</a> for further help.'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_ORGANISATION

    def process(self, grant, path_prefix):
        try:
            count_failure = False
            for num, organization in enumerate(grant["recipientOrganization"]):
                for prefix in orgids_prefixes:
                    if organization["id"].lower().startswith(prefix.lower()):
                        break
                else:
                    self.failed = True
                    count_failure = True
                    self.json_locations.append(
                        path_prefix + "/recipientOrganization/{}/id".format(num)
                    )

            if count_failure:
                self.count += 1
        except KeyError:
            pass

        self.heading = mark_safe(
            self.format_heading_count(
                self.check_text["heading"], test_class_type=QUALITY_TEST_CLASS
            )
        )
        self.message = self.check_text["message"][self.grants_percentage]


class FundingOrgUnrecognisedPrefix(AdditionalTest):
    """Check if any grants have FundingOrg IDs that use a prefix that isn't on the Org ID prefix codelist"""

    check_text = {
        "heading": mark_safe(
            'a <span class="highlight-background-text">Funding Org:Identifier</span> '
            "that does not draw from a recognised register"
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "In the 360Giving Data Standard, organisation identifiers have two parts: an "
        "identifier and a prefix which describes the list the identifier is taken from. "
        "This error notice is caused by the prefix in an organisation identifier not "
        'being taken from a recognised register from the <a target="_blank" href="https://org-id.guide/">org-id list locator</a>. See our '
        '<a target="_blank" href="https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier">guidance on organisation identifiers</a> for further help.'
    )

    def process(self, grant, path_prefix):
        try:
            count_failure = False
            for num, organization in enumerate(grant["fundingOrganization"]):
                for prefix in orgids_prefixes:
                    if organization["id"].lower().startswith(prefix.lower()):
                        break
                else:
                    self.failed = True
                    count_failure = True
                    self.json_locations.append(
                        path_prefix + "/fundingOrganization/{}/id".format(num)
                    )

            if count_failure:
                self.count += 1
        except KeyError:
            pass

        self.heading = mark_safe(
            self.format_heading_count(
                self.check_text["heading"], test_class_type=QUALITY_TEST_CLASS
            )
        )
        self.message = self.check_text["message"][self.grants_percentage]


class RecipientOrgCharityNumber(AdditionalTest):
    """Check if any grants have RecipientOrg charity numbers that don't look like charity numbers

    Checks if the first two characters are letters, then checks that the remainder of the value is a number
    6 or 7 digits long.
    """

    check_text = {
        "heading": mark_safe(
            "a value provided in the "
            '<span class="highlight-background-text">Recipient Org:Charity Number</span> '
            "column that doesn’t look like a UK charity number"
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Common causes of this error notice are missing or extra digits, typos or "
        "incorrect values such as text appearing in this field. You can check UK charity "
        'numbers online at <a target="_blank" href="https://findthatcharity.uk/">FindthatCharity</a>. This error may also be triggered by '
        "correctly formatted non-UK charity numbers, in which case this message can be "
        "ignored."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_ORGANISATION

    def process(self, grant, path_prefix):
        try:
            count_failure = False
            for num, organization in enumerate(grant["recipientOrganization"]):
                charity_number = organization["charityNumber"]
                charity_number = str(charity_number)
                if charity_number[:2].isalpha():
                    charity_number = charity_number[2:]
                if not check_charity_number(charity_number):
                    self.failed = True
                    count_failure = True
                    self.json_locations.append(
                        path_prefix
                        + "/recipientOrganization/{}/charityNumber".format(num)
                    )

            if count_failure:
                self.count += 1
        except KeyError:
            pass

        self.heading = mark_safe(
            self.format_heading_count(
                self.check_text["heading"], test_class_type=QUALITY_TEST_CLASS
            )
        )
        self.message = self.check_text["message"][self.grants_percentage]


class RecipientOrgCompanyNumber(AdditionalTest):
    """Checks if any grants have RecipientOrg company numbers that don't look like company numbers

    Checks if the value is 8 characters long, and that the last 6 of those characters are numbers
    """

    check_text = {
        "heading": mark_safe(
            "a value provided in the "
            '<span class="highlight-background-text">Recipient Org:Company Number</span> '
            "column that doesn’t look like a company number"
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Common causes of this error notice are missing or extra digits, typos or "
        "incorrect values such as text appearing in this field. UK Company numbers are "
        'typically 8 digits, for example <span class="highlight-background-text">09876543</span> or sometimes start with a 2 letter '
        'prefix, <span class="highlight-background-text">SC123459</span>. '
        'You can check company numbers online at <a target="_blank" href="https://find-and-update.company-information.service.gov.uk/">Companies House</a>. '
        "This error may also be triggered by correctly formatted non-UK company numbers, "
        "in which case this message can be ignored."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_ORGANISATION

    def process(self, grant, path_prefix):
        try:
            count_failure = False
            for num, organization in enumerate(grant["recipientOrganization"]):
                company_number = organization["companyNumber"]
                if not check_company_number(company_number):
                    self.failed = True
                    count_failure = True
                    self.json_locations.append(
                        path_prefix
                        + "/recipientOrganization/{}/companyNumber".format(num)
                    )

            if count_failure:
                self.count += 1
        except KeyError:
            pass

        self.heading = mark_safe(
            self.format_heading_count(
                self.check_text["heading"], test_class_type=QUALITY_TEST_CLASS
            )
        )
        self.message = mark_safe(self.check_text["message"][self.grants_percentage])


class NoRecipientOrgCompanyCharityNumber(AdditionalTest):
    """Checks if any grants don't have either a Recipient Org:Company Number or Recipient Org:Charity Number"""

    check_text = {
        "heading": mark_safe(
            "not have either a "
            '<span class="highlight-background-text">Recipient Org:Company Number</span> or a '
            '<span class="highlight-background-text">Recipient Org:Charity Number</span>'
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Company and charity numbers are important for understanding grantmaking in the "
        "UK and including these separately makes it easier for users to match grants "
        "data with official sources of information about the recipients. If your grants "
        "are to organisations that don’t have UK Company or UK Charity numbers, you can "
        "ignore this notice."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_ORGANISATION

    def process(self, grant, path_prefix):
        try:
            count_failure = False
            for num, organization in enumerate(grant["recipientOrganization"]):
                has_id_number = organization.get("companyNumber") or organization.get(
                    "charityNumber"
                )
                if not has_id_number:
                    self.failed = True
                    count_failure = True
                    self.json_locations.append(
                        path_prefix + "/recipientOrganization/{}/id".format(num)
                    )

            if count_failure:
                self.count += 1
        except KeyError:
            pass

        self.heading = mark_safe(
            self.format_heading_count(self.check_text["heading"], verb="do")
        )
        self.message = self.check_text["message"][self.grants_percentage]


class IncompleteRecipientOrg(AdditionalTest):
    """
    Checks if any grants lack one of either Recipient Org:Postal Code or both of Recipient Org:Location:Geographic Code
    and Recipient Org:Location:Geographic Code Type
    """

    check_text = {
        "heading": mark_safe("not have recipient organisation location information"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Recipient location data in the form of postcodes or geocodes provides a "
        "consistent way to describe a location. This data can be used to produce maps, "
        "such as the maps in "
        '<a target="_blank" href="https://insights.threesixtygiving.org/">360Insights</a>, '
        "showing the geographical distribution of "
        "funding and allows grants data to be looked at alongside official statistics, "
        "such as the Indices of multiple deprivation. See our "
        '<a target="_blank" href="https://standard.threesixtygiving.org/en/latest/guidance/location-guide/">guidance on location data</a> '
        "for further help. "
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_ORGANISATION

    def process(self, grant, path_prefix):
        try:
            count_failure = False
            for num, organization in enumerate(grant["recipientOrganization"]):
                has_postal_code = organization.get("postalCode")
                has_location_data = organization.get("location") and any(
                    location.get("geoCode") and location.get("geoCodeType")
                    for location in organization.get("location")
                )

                complete_recipient_org_data = has_postal_code or has_location_data
                if not complete_recipient_org_data:
                    self.failed = True
                    count_failure = True
                    self.json_locations.append(
                        path_prefix + "/recipientOrganization/{}/id".format(num)
                    )
            if count_failure:
                self.count += 1
        except KeyError:
            pass

        self.heading = self.format_heading_count(self.check_text["heading"], verb="do")
        self.message = mark_safe(self.check_text["message"][self.grants_percentage])


class MoreThanOneFundingOrg(AdditionalTest):
    """Checks if the file contains multiple FundingOrganisation:IDs"""

    check_text = {
        "heading": mark_safe("{} different funding organisation identifiers listed"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "If you are only publishing for a single funder then you should review your "
        '<span class="highlight-background-text">Funding Organisation identifier</span> field '
        "to see where multiple IDs have occurred. "
        "If you are expecting to be publishing data for multiple funders and the number "
        "of funders is correct, then you can ignore this error notice."
    )

    def __init__(self, **kw):
        super().__init__(**kw)
        self.funding_organization_ids = []

    def process(self, grant, path_prefix):
        try:
            for num, organization in enumerate(grant["fundingOrganization"]):
                if (
                    organization.get("id")
                    and organization.get("id") not in self.funding_organization_ids
                ):
                    self.funding_organization_ids.append(organization["id"])
                    self.json_locations.append(
                        path_prefix + "/fundingOrganization/{}/id".format(num)
                    )
        except KeyError:
            pass
        if len(self.funding_organization_ids) > 1:
            self.failed = True

        self.heading = self.check_text["heading"].format(
            len(self.funding_organization_ids)
        )
        self.message = mark_safe(self.check_text["message"][self.grants_percentage])


compiled_email_re = re.compile("[\w.-]+@[\w.-]+\.[\w.-]+")


class LooksLikeEmail(AdditionalTest):
    """Checks if any grants contain text that looks like an email address

    The check looks for any number of alphanumerics, dots or hyphens, followed by an @ sign, followed by any number of
    alphanumerics, dots or hyphens, with a minimum of one dot after the @
    """

    check_text = {
        "heading": mark_safe("text that looks like an email address"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data may contain an email address (or something that looks like "
        "one), which can constitute personal data if it is the email of an "
        "individual. The use and distribution of personal data is restricted by "
        "the Data Protection Act. You should ensure that any personal data is "
        "removed from your data prior to publishing it, or that it is only "
        "included with the knowledge and consent of the person to whom it "
        "refers."
    )

    def process(self, grant, path_prefix):
        flattened_grant = OrderedDict(flatten_dict(grant))
        for key, value in flattened_grant.items():
            if "email" in key:
                continue
            if isinstance(value, str) and compiled_email_re.search(value):
                self.failed = True
                self.json_locations.append(path_prefix + key)
                self.count += 1

        self.heading = self.format_heading_count(
            self.check_text["heading"],
            test_class_type=QUALITY_TEST_CLASS,
            verb="contain",
        )
        self.message = self.check_text["message"][self.grants_percentage]


class NoGrantProgramme(AdditionalTest):
    """Checks if any grants have no Grant Programme fields"""

    check_text = {
        "heading": mark_safe(
            'not contain any <span class="highlight-background-text">Grant Programme</span> fields'
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Grant programme names help users to understand a funder’s different types of "
        "funding and priorities, and see how their grants vary across and within these. "
        "This information is especially useful when it refers to the communities, "
        "sectors, issues or places that are the focus of the programme. If your "
        "organisation does not have grant programmes this notice can be ignored."
    )

    def process(self, grant, path_prefix):
        grant_programme = grant.get("grantProgramme")
        if not grant_programme:
            self.failed = True
            self.count += 1
            self.json_locations.append(path_prefix + "/id")

        self.heading = mark_safe(
            self.format_heading_count(self.check_text["heading"], verb="do")
        )
        self.message = mark_safe(self.check_text["message"][self.grants_percentage])


class NoBeneficiaryLocation(AdditionalTest):
    """Checks if any grants have no Beneficiary Location fields"""

    check_text = {
        "heading": mark_safe("not contain any beneficiary location fields"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Beneficiary location data in the form of place names and geocodes allow users "
        "to understand which places funding is reaching. This data can be more accurate "
        "in showing where grants are going geographically, especially in cases where the "
        "recipient location is in a different place from the activity being funded. "
        "Beneficiary location codes can be used to produce maps, such as the ones in "
        '<a target="_blank" href="https://insights.threesixtygiving.org/">360Insights</a>, '
        "showing the geographical distribution of funding and allows grants "
        "data to be looked at alongside official statistics, such as the Indices of "
        "multiple deprivation. See our "
        '<a target="_blank" href="https://standard.threesixtygiving.org/en/latest/guidance/location-guide/">guidance on location data </a>'
        "for further help."
    )

    def process(self, grant, path_prefix):
        beneficiary_location = grant.get("beneficiaryLocation")
        if not beneficiary_location:
            self.failed = True
            self.count += 1
            self.json_locations.append(path_prefix + "/id")

        self.heading = self.format_heading_count(self.check_text["heading"], verb="do")
        self.message = self.check_text["message"][self.grants_percentage]


class TitleDescriptionSame(AdditionalTest):
    """Checks if any grants have the same text for Title and Description"""

    check_text = {
        "heading": mark_safe("a title and a description that are the same"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Users may find that the data is less useful as they are unable to discover more about the grants. "
        "Consider including a more detailed description if you have one."
    )

    def process(self, grant, path_prefix):
        title = grant.get("title")
        description = grant.get("description")
        if title and description and title == description:
            self.failed = True
            self.count += 1
            self.json_locations.append(path_prefix + "/description")

        self.heading = self.format_heading_count(self.check_text["heading"])
        self.message = self.check_text["message"][self.grants_percentage]


class TitleLength(AdditionalTest):
    """Checks if any grants have Titles longer than 140 characters"""

    check_text = {
        "heading": mark_safe("a title that is longer than recommended"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Titles for grant activities should be under 140 characters long so that people "
        "can quickly understand the purpose of the grant."
    )

    def process(self, grant, path_prefix):
        title = grant.get("title", "")
        if len(title) > 140:
            self.failed = True
            self.count += 1
            self.json_locations.append(path_prefix + "/title")

        self.heading = self.format_heading_count(self.check_text["heading"])
        self.message = self.check_text["message"][self.grants_percentage]


class OrganizationIdLooksInvalid(AdditionalTest):
    """Checks if any grants have org IDs for fundingOrg or recipientOrg that don't look correctly formatted for their
    respective registration agency (eg GB-CHC- not looking like a valid company number)

    Looks at the start of the ID - if it's GB-CHC- or GB-COH-, performs the relevant format check
    """

    check_text = {
        "heading": mark_safe("a Funding or Recipient Organisation identifier that might not be valid"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "The identifiers might not be valid for the recognised register that they refer "
        "to - for example, an identifier with the prefix 'GB-CHC' that contains an "
        "invalid charity number. Common causes of this are missing or extra digits, "
        "typos or incorrect values such as text appearing in this field. See our "
        '<a target="_blank" href="https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier">guidance on organisation identifiers</a> '
        "for further help."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_ORGANISATION

    def process(self, grant, path_prefix):
        for org_type in ("fundingOrganization", "recipientOrganization"):
            orgs = grant.get(org_type, [])
            for num, org in enumerate(orgs):
                org_id = org.get("id")
                if not org_id:
                    continue
                id_location = "{}/{}/{}/id".format(path_prefix, org_type, num)
                if org_id.upper().startswith("GB-CHC-"):
                    if not check_charity_number(org_id[7:]):
                        self.failed = True
                        self.json_locations.append(id_location)
                        self.count += 1
                elif org_id.upper().startswith("GB-COH-"):
                    if not check_company_number(org_id[7:]):
                        self.failed = True
                        self.json_locations.append(id_location)
                        self.count += 1

        self.heading = self.format_heading_count(
            self.check_text["heading"], test_class_type=QUALITY_TEST_CLASS
        )
        self.message = self.check_text["message"][self.grants_percentage]


class NoLastModified(AdditionalTest):
    """Check if any grants are missing Last Modified dates"""

    check_text = {
        "heading": mark_safe(
            'not have <span class="highlight-background-text">Last Modified</span> information'
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        '<span class="highlight-background-text">Last Modified</span> shows the date and time when '
        "information about a grant was last updated in your file. Including this information allows data "
        "users to see when changes have been made and reconcile differences between versions of your data."
    )

    def process(self, grant, path_prefix):
        last_modified = grant.get("dateModified")
        if not last_modified:
            self.failed = True
            self.count += 1
            self.json_locations.append(path_prefix + "/id")

        self.heading = mark_safe(
            self.format_heading_count(self.check_text["heading"], verb="do")
        )
        self.message = mark_safe(self.check_text["message"][self.grants_percentage])


class NoDataSource(AdditionalTest):
    """Checks if any grants are missing dataSource"""

    check_text = {
        "heading": mark_safe(
            'not have <span class="highlight-background-text">Data Source</span> information'
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        '<span class="highlight-background-text">Data Source</span> is a web link pointing to the source of this data. '
        "It informs users about where "
        "information came from and is an important part of establishing trust in your data. "
        "This may be a link to an "
        "original 360Giving data file, a file from which the data was converted, or your organisation’s "
        "website."
    )

    def process(self, grant, path_prefix):
        data_source = grant.get("dataSource")
        if not data_source:
            self.failed = True
            self.count += 1
            self.json_locations.append(path_prefix + "/id")

        self.heading = mark_safe(
            self.format_heading_count(self.check_text["heading"], verb="do")
        )
        self.message = mark_safe(self.check_text["message"][self.grants_percentage])


class ImpossibleDates(AdditionalTest):
    """
    Check if dates supplied are plausible (eg no 31st Feb) or
    are plausible but didn't happen (eg 29th of Feb in a non-leap year).
    """

    check_text = {
        "heading": mark_safe("dates that don’t exist"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data contains dates that didn't, or won't, exist - such as the 31st of September, "
        "or the 29th of February in a year that's not a leap year. This error is commonly caused by typos during data entry."
    )

    def process(self, grant, path_prefix):
        grant_dates = create_grant_dates_dict(Grant(grant))

        if grant_dates:
            for date_type, date_format_error in (
                [
                    "award_date",
                    grant_dates.get("award_date", {}).get("date_format_error"),
                ],
                [
                    "planned_start_date",
                    grant_dates.get("planned_start_date", {}).get("date_format_error"),
                ],
                [
                    "planned_end_date",
                    grant_dates.get("planned_end_date", {}).get("date_format_error"),
                ],
                [
                    "actual_start_date",
                    grant_dates.get("actual_start_date", {}).get("date_format_error"),
                ],
                [
                    "actual_end_date",
                    grant_dates.get("actual_end_date", {}).get("date_format_error"),
                ],
            ):
                if date_format_error:
                    if (
                        "does not match format '%Y-%m-%d'" not in date_format_error
                    ) and ("unconverted data remains" not in date_format_error):
                        self.failed = True
                        self.count += 1
                        self.json_locations.append(
                            path_prefix + DATES_JSON_LOCATION[date_type]
                        )
                        break

        self.heading = self.format_heading_count(self.check_text["heading"])
        self.message = self.check_text["message"][self.grants_percentage]


class PlannedStartDateBeforeEndDate(AdditionalTest):
    """Check if Planned Dates:Start Date is after Planned Dates:End Date"""

    check_text = {
        "heading": mark_safe(
            '<span class="highlight-background-text">Planned Dates:Start Date</span> entries that are after the '
            'corresponding <span class="highlight-background-text">Planned Dates:End Date</span>'
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "This can happen when the fields are accidentally reversed, or if there is a typo in the date. "
        "This can also be caused by inconsistent date formatting when data was prepared using spreadsheet software."
    )

    def process(self, grant, path_prefix):
        grant_dates = create_grant_dates_dict(Grant(grant))

        if grant_dates:
            planned_start_date = grant_dates.get("planned_start_date", {}).get(
                "datetime_date"
            )
            planned_end_date = grant_dates.get("planned_end_date", {}).get(
                "datetime_date"
            )

            if planned_start_date and planned_end_date:
                if planned_start_date > planned_end_date:
                    self.failed = True
                    self.count += 1
                    self.json_locations.append(
                        path_prefix + DATES_JSON_LOCATION["planned_start_date"]
                    )

        self.heading = mark_safe(self.format_heading_count(self.check_text["heading"]))
        self.message = self.check_text["message"][self.grants_percentage]


class ActualStartDateBeforeEndDate(AdditionalTest):
    """Check if Actual Dates:Start Date is after Actual Dates:End Date'"""

    check_text = {
        "heading": mark_safe(
            '<span class="highlight-background-text">Actual Dates:Start Date</span> entries that are after the '
            'corresponding <span class="highlight-background-text">Actual Dates:End Date</span>'
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "This can happen when the fields are accidentally reversed, or if there is a typo in the date. "
        "This can also be caused by inconsistent date formatting when data was prepared using spreadsheet software."
    )

    def process(self, grant, path_prefix):
        grant_dates = create_grant_dates_dict(Grant(grant))

        if grant_dates:
            actual_start_date = grant_dates.get("actual_start_date", {}).get(
                "datetime_date"
            )
            actual_end_date = grant_dates.get("actual_end_date", {}).get(
                "datetime_date"
            )

            if actual_start_date and actual_end_date:
                if actual_start_date > actual_end_date:
                    self.failed = True
                    self.count += 1
                    self.json_locations.append(
                        path_prefix + DATES_JSON_LOCATION["actual_start_date"]
                    )

        self.heading = mark_safe(self.format_heading_count(self.check_text["heading"]))
        self.message = self.check_text["message"][self.grants_percentage]


class FarFuturePlannedDates(AdditionalTest):
    """Check if dates in plannedDates are > 12 years into the future, from the present day."""

    check_text = {
        "heading": mark_safe("Planned Dates that are over 12 years in the future"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data contains Planned Dates that are more than 12 years into the future. You can disregard this error notice if "
        "your data describes activities that run a long time into the future, but you should check for data entry "
        "errors if this isn't expected."
    )

    def process(self, grant, path_prefix):
        grant_dates = create_grant_dates_dict(Grant(grant))

        if grant_dates:
            for date_type, input_date in (
                [
                    "planned_start_date",
                    grant_dates.get("planned_start_date", {}).get("datetime_date"),
                ],
                [
                    "planned_end_date",
                    grant_dates.get("planned_end_date", {}).get("datetime_date"),
                ],
            ):
                if input_date:
                    if input_date > datetime.datetime.now() + relativedelta(years=12):
                        self.failed = True
                        self.count += 1
                        self.json_locations.append(
                            path_prefix + DATES_JSON_LOCATION[date_type]
                        )
                        break

        self.heading = self.format_heading_count(self.check_text["heading"])
        self.message = self.check_text["message"][self.grants_percentage]


class FarFutureActualDates(AdditionalTest):
    """Check if dates in actualDates are > 5 years into the future, from the present day."""

    check_text = {
        "heading": mark_safe("Actual Date entries that are over 5 years in the future"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data contains Actual Date entries that are more than 5 years into the future. You can disregard this "
        "error notice if your data describes activities far in the future, but you should check for data entry errors "
        "if this isn't expected."
    )

    def process(self, grant, path_prefix):
        grant_dates = create_grant_dates_dict(Grant(grant))

        if grant_dates:
            for date_type, input_date in (
                [
                    "actual_start_date",
                    grant_dates.get("actual_start_date", {}).get("datetime_date"),
                ],
                [
                    "actual_end_date",
                    grant_dates.get("actual_end_date", {}).get("datetime_date"),
                ],
            ):
                if input_date:
                    if input_date > datetime.datetime.now() + relativedelta(years=5):
                        self.failed = True
                        self.count += 1
                        self.json_locations.append(
                            path_prefix + DATES_JSON_LOCATION[date_type]
                        )
                        break

        self.heading = self.format_heading_count(self.check_text["heading"])
        self.message = self.check_text["message"][self.grants_percentage]


class FarPastDates(AdditionalTest):
    """Check if dates in awardDate, plannedDates, actualDates are > 25 years in the past, from the present day."""

    check_text = {
        "heading": mark_safe("dates that are over 25 years ago"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data contains dates that are more than 25 years ago. You can disregard this error notice if your "
        "data is about activities far in the past, but you should check for data entry errors if this isn't expected."
    )

    def process(self, grant, path_prefix):
        grant_dates = create_grant_dates_dict(Grant(grant))

        if grant_dates:
            for date_type, input_date in (
                ["award_date", grant_dates.get("award_date", {}).get("datetime_date")],
                [
                    "planned_start_date",
                    grant_dates.get("planned_start_date", {}).get("datetime_date"),
                ],
                [
                    "planned_end_date",
                    grant_dates.get("planned_end_date", {}).get("datetime_date"),
                ],
                [
                    "actual_start_date",
                    grant_dates.get("actual_start_date", {}).get("datetime_date"),
                ],
                [
                    "actual_end_date",
                    grant_dates.get("actual_end_date", {}).get("datetime_date"),
                ],
            ):

                if input_date:
                    if input_date < datetime.datetime.now() - relativedelta(years=25):
                        self.failed = True
                        self.count += 1
                        self.json_locations.append(
                            path_prefix + DATES_JSON_LOCATION[date_type]
                        )
                        break

        self.heading = self.format_heading_count(self.check_text["heading"])
        self.message = self.check_text["message"][self.grants_percentage]


class PostDatedAwardDates(AdditionalTest):
    """Check if dates in awardDate is in the future, from the present day."""

    check_text = {
        "heading": mark_safe("Award Dates that are in the future"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data contains grant Award Dates in the future. This date is when the decision to award the grant "
        "was made so it would normally be in the past. This error can happen when there is a typo in the date, or the data "
        "includes grants that are not yet fully committed"
    )

    def process(self, grant, path_prefix):
        grant_dates = create_grant_dates_dict(Grant(grant))

        if grant_dates:
            award_date = grant_dates.get("award_date", {}).get("datetime_date")
            if award_date:
                if award_date > datetime.datetime.now():
                    self.failed = True
                    self.count += 1
                    self.json_locations.append(
                        path_prefix + DATES_JSON_LOCATION["award_date"]
                    )

        self.heading = self.format_heading_count(self.check_text["heading"])
        self.message = self.check_text["message"][self.grants_percentage]


class RecipientIndWithoutToIndividualsDetails(AdditionalTest):
    """Check for grants with recipientIndividual, but no toIndividualsDetails."""

    check_text = {
        "heading": mark_safe(
            '<span class="highlight-background-text">Recipient Ind</span> but no '
            '<span class="highlight-background-text">To Individuals Details:Grant Purpose</span> or '
            '<span class="highlight-background-text">To Individuals Details:Primary Grant Reason</span>'
        ),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data contains grants to individuals, but without the grant "
        "purpose or grant reason codes. This can make it difficult to use data "
        "on grants to individuals, as much of the information is anonymised, so "
        "it is recommended that you share these codes for all grants to "
        "individuals."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_INDIVIDUAL

    def process(self, grant, path_prefix):
        if "recipientIndividual" in grant and "toIndividualsDetails" not in grant:
            self.failed = True
            self.count += 1
            self.json_locations.append(
                path_prefix + "/recipientIndividual/id"
            )

        self.heading = mark_safe(self.format_heading_count(self.check_text["heading"]))
        self.message = self.check_text["message"][self.grants_percentage]


class RecipientIndDEI(AdditionalTest):
    """Check for grants with recipientIndividual, and DEI info (under "project")."""

    check_text = {
        "heading": mark_safe('<span class="highlight-background-text">Recipient Ind</span> and DEI information'),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data contains grants to individuals which also have DEI "
        "(Diversity, Equity and Inclusion) information. You must not share any "
        "DEI data about individuals as this can make them personally "
        "identifiable when combined with other information in the grant."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_INDIVIDUAL

    def process(self, grant, path_prefix):
        if "recipientIndividual" in grant and "project" in grant:
            self.failed = True
            self.count += 1
            self.json_locations.append(
                path_prefix + "/recipientIndividual/id"
            )

        self.heading = mark_safe(self.format_heading_count(self.check_text["heading"]))
        self.message = self.check_text["message"][self.grants_percentage]


# Postcode regex from https://ideal-postcodes.co.uk/guides/postcode-validation
# "Simple Regular Expression"
# This is a simple regex, for something that "looks roughly like a postcode",
# which is all we need here.
# Modified to match when there are accidental leading and trailing spaces.
postcode_re = re.compile("^\s*[a-z]{1,2}\d[a-z\d]?\s*\d[a-z]{2}\s*$", re.IGNORECASE)


# Note that we ignore Geographic Code Type here because people putting in
# postcodes don't tend to use that properly.
class GeoCodePostcode(AdditionalTest):
    """Check for grants with a beneficiaryLocation geoCode that looks like a postcode."""

    check_text = {
        "heading": mark_safe("Geographic Code that looks like a postcode"),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data contains a "
        '<span class="highlight-background-text">Beneficiary Location:Geographic Code</span> '
        "that looks like a postcode on grants to individuals. You must not "
        "share any postcodes for grants to individuals as this can make them "
        "personally identifiable when combined with other information in the "
        "grant."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = RECIPIENT_INDIVIDUAL

    def process(self, grant, path_prefix):
        if "recipientIndividual" in grant:
            for num, beneficiary_location in enumerate(grant.get("beneficiaryLocation", [])):
                geo_code = beneficiary_location.get("geoCode", "")
                if postcode_re.match(geo_code):
                    self.failed = True
                    self.count += 1
                    self.json_locations.append(
                        "{}/beneficiaryLocation/{}/geoCode".format(path_prefix, num)
                    )

        self.heading = self.format_heading_count(self.check_text["heading"])
        self.message = self.check_text["message"][self.grants_percentage]


TEST_CLASSES = {
    QUALITY_TEST_CLASS: [
        ZeroAmountTest,
        FundingOrgUnrecognisedPrefix,
        RecipientOrgUnrecognisedPrefix,
        RecipientOrgCharityNumber,
        RecipientOrgCompanyNumber,
        OrganizationIdLooksInvalid,
        MoreThanOneFundingOrg,
        LooksLikeEmail,
        ImpossibleDates,
        PlannedStartDateBeforeEndDate,
        ActualStartDateBeforeEndDate,
        FarFuturePlannedDates,
        FarFutureActualDates,
        FarPastDates,
        PostDatedAwardDates,
        RecipientIndWithoutToIndividualsDetails,
        RecipientIndDEI,
        GeoCodePostcode,
    ],
    USEFULNESS_TEST_CLASS: [
        RecipientOrg360GPrefix,
        FundingOrg360GPrefix,
        NoRecipientOrgCompanyCharityNumber,
        IncompleteRecipientOrg,
        NoGrantProgramme,
        NoBeneficiaryLocation,
        TitleDescriptionSame,
        TitleLength,
        NoLastModified,
        NoDataSource,
    ],
}


def convert_string_date_to_datetime(input_date):
    """
    Date format that will be converted are:

    YYYY-MM-DD
    YYYY-MM-DDT...
    """
    error_msg = None
    datetime_date = None

    if "T" in input_date:
        input_date = input_date.split("T")[0]
        convert_string_date_to_datetime(input_date)

    try:
        datetime_date = datetime.datetime.strptime(input_date, "%Y-%m-%d")
    except ValueError as e:
        error_msg = str(e)

    return datetime_date, error_msg


class Grant:
    def __init__(self, grant):
        self.grant = grant

    def __hash__(self):
        return hash(self.grant.get("id"))


@functools.lru_cache(maxsize=None)
def create_grant_dates_dict(grant):
    """
    Creates the following dict:

    grant_dates: { 'date_type': {'datetime_date': datetime_date, 'date_format_error': error_msg}}
    """
    grant_dates = {}

    award_date = grant.grant.get("awardDate")
    planned_start_date = grant.grant.get("plannedDates", [{}])[0].get("startDate")
    planned_end_date = grant.grant.get("plannedDates", [{}])[0].get("endDate")
    actual_start_date = grant.grant.get("actualDates", [{}])[0].get("startDate")
    actual_end_date = grant.grant.get("actualDates", [{}])[0].get("endDate")

    for date_type, input_date in [
        ["award_date", award_date],
        ["planned_start_date", planned_start_date],
        ["planned_end_date", planned_end_date],
        ["actual_start_date", actual_start_date],
        ["actual_end_date", actual_end_date],
    ]:
        if input_date:
            datetime_date, error_msg = convert_string_date_to_datetime(input_date)

            grant_dates[date_type] = {
                "datetime_date": datetime_date,
                "date_format_error": error_msg,
            }

    return grant_dates


@tools.ignore_errors
def run_extra_checks(json_data, cell_source_map, test_classes, aggregates):
    if "grants" not in json_data:
        return []

    test_instances = [test_cls(grants=json_data["grants"], aggregates=aggregates) for test_cls in test_classes]

    for num, grant in enumerate(json_data["grants"]):
        for test_instance in test_instances:
            test_instance.process(grant, "grants/{}".format(num))

    results = []

    for test_instance in test_instances:
        if not test_instance.failed:
            continue

        spreadsheet_locations = []
        spreadsheet_keys = ("sheet", "letter", "row_number", "header")
        if cell_source_map:
            try:
                spreadsheet_locations = [
                    dict(zip(spreadsheet_keys, cell_source_map[location][0]))
                    for location in test_instance.json_locations
                ]
            except KeyError:
                continue
        results.append(
            (
                test_instance.produce_message(),
                test_instance.json_locations,
                spreadsheet_locations,
            )
        )
    return results
