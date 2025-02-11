from lib360dataquality.additional_test import AdditionalTest, TestRelevance, RangeDict
from functools import wraps

try:
    from django.utils.html import mark_safe
except ImportError:
    # If we don't have django we're not using this lib in CoVE so we're not using the output
    # in HTML and therefore do not need a SafeString object.
    def mark_safe(string):
        return string


class FieldNotPresentBase(AdditionalTest):
    """Checks if any grants do not have a specified field"""

    # Field should be overridden and specified as a path
    # e.g. /awardDate
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.check_text = {
            "heading": "not contain %s field" % self.field,
            "message": "Providing %s field helps people to understand the grant information."
            % self.field,
        }

    def process(self, grant, path_prefix):
        if not self.field:
            raise Exception("Field to check for not set")

        if not self.check_field(grant):
            self.failed = True
            self.count += 1
            self.json_locations.append(path_prefix + "/id")

        self.heading = self.format_heading_count(self.check_text["heading"], verb="do")
        self.message = self.check_text["message"]


# exception to false is a decorator rather than handling it in process()
# this is so that we don't get strange interactions with @ignore_errors decorator
# which is already present on the caller of the process function
def exception_to_false(f):
    """If the function returns a KeyError or IndexError exception it is treated as false"""

    @wraps(f)
    def check(self, grant):
        try:
            return f(self, grant)
        except (KeyError, IndexError):
            return False

    return check


class ClassificationNotPresent(FieldNotPresentBase):
    field = "classifications/0/title"

    @exception_to_false
    def check_field(self, grant):
        return grant["classifications"][0]["title"]


class BeneficiaryLocationNameNotPresent(FieldNotPresentBase):
    field = "beneficiaryLocation/0/name"

    @exception_to_false
    def check_field(self, grant):
        return grant["beneficiaryLocation"][0]["name"]


class BeneficiaryLocationCountryCodeNotPresent(FieldNotPresentBase):
    field = "beneficiaryLocation/0/countryCode"

    @exception_to_false
    def check_field(self, grant):
        return grant["beneficiaryLocation"][0]["countryCode"]


class BeneficiaryLocationGeoCodeNotPresent(FieldNotPresentBase):
    field = "beneficiaryLocation/0/geoCode"

    @exception_to_false
    def check_field(self, grant):
        return grant["beneficiaryLocation"][0]["geoCode"]


class PlannedDurationNotPresent(FieldNotPresentBase):
    """ Checks for either a planned duration or start and end dates"""

    check_text = {
        "heading": mark_safe('Neither a planned duration or start and end dates found'),
        "message": RangeDict(),
    }
    check_text["message"][(0, 100)] = mark_safe(
        "Your data does not contain either a planned duration or a start and end date."
    )

    field = (
        "plannedDates/0/duration or (plannedDates/startDate and plannedDates/endDate)"
    )

    @exception_to_false
    def check_field(self, grant):
        return (grant["plannedDates"][0].get("duration") or (grant["plannedDates"][0].get("startDate") and grant["plannedDates"][0].get("endDate")))


class GrantProgrammeTitleNotPresent(FieldNotPresentBase):
    field = "grantProgramme/0/title"

    @exception_to_false
    def check_field(self, grant):
        return grant["grantProgramme"][0]["title"]


class IndividualsCodeListsNotPresent(FieldNotPresentBase):
    field = (
        "toIndividualsDetails/grantPurpose or toIndividualsDetails/primaryGrantReason"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.relevant_grant_type = TestRelevance.RECIPIENT_INDIVIDUAL

    def check_field(self, grant):
        # Not relevant
        if not grant.get("recipientIndividual"):
            return True

        details = grant.get("toIndividualsDetails")
        if details:
            return (
                len(details.get("grantPurpose", [])) > 0
                or len(details.get("primaryGrantReason", "")) > 0
            )
        return False
