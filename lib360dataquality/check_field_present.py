from lib360dataquality.cove.threesixtygiving import AdditionalTest
from functools import wraps


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

        if self.check_field(grant) is False:
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
            f(self, grant)
            return True
        except (KeyError, IndexError):
            return False

    return check


class ClassificationNotPresent(FieldNotPresentBase):
    field = "classifications"

    @exception_to_false
    def check_field(self, grant):
        return grant["classifications"]


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
    field = "plannedDates/0/duration"

    @exception_to_false
    def check_field(self, grant):
        return grant["plannedDates"][0]["duration"]


class GrantProgrammeTitleNotPresent(FieldNotPresentBase):
    field = "grantProgramme/0/title"

    @exception_to_false
    def check_field(self, grant):
        return grant["grantProgramme"][0]["title"]
