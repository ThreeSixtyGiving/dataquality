from rangedict import RangeDict as range_dict
from collections import OrderedDict


class TestType(object):
    QUALITY_TEST_CLASS = "quality_accuracy"
    USEFULNESS_TEST_CLASS = "usefulness"


class TestRelevance(object):
    RECIPIENT_ANY = ""
    RECIPIENT_ORGANISATION = "recipient organisation"
    RECIPIENT_INDIVIDUAL = "recipient individual"


class TestCategories(object):
    GRANTS = "Grants"
    ORGANISATIONS = "Organisations"
    DATA_PROTECTION = "Data Protection"
    DATES = "Dates"
    LOCATION = "Location"
    METADATA = "Metadata"


class TestImportance(object):
    CRITICAL = 100
    NONE = 0


class AdditionalTest(object):
    category = TestCategories.GRANTS
    importance = TestImportance.NONE

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
        self.relevant_grant_type = TestRelevance.RECIPIENT_ANY

    def process(self, grant, path_prefix):
        # Each test must implement this function which is called on each grant after
        # the class is initialised.
        # Set self.count, self.failed, self.heading and self.message
        pass

    def produce_message(self):
        return {
            "heading": self.heading,
            "message": self.message,
            "type": self.__class__.__name__,
            "count": self.count,
            "percentage": self.grants_percentage,
            "category": self.__class__.category,
            "importance": self.__class__.importance,
        }

    def get_heading_count(self, test_class_type):
        # The total grants is contextual e.g. a test may fail for a recipient org-id
        # this is only relevant to grants to organisations and not individuals
        if self.relevant_grant_type == TestRelevance.RECIPIENT_ANY:
            total = self.aggregates["count"]
        elif self.relevant_grant_type == TestRelevance.RECIPIENT_ORGANISATION:
            total = self.aggregates["count"] - self.aggregates["recipient_individuals_count"]
        elif self.relevant_grant_type == TestRelevance.RECIPIENT_INDIVIDUAL:
            # if there are no individuals in this data then reset the count
            if self.aggregates["recipient_individuals_count"] == 0:
                self.count = 0
            total = self.aggregates["recipient_individuals_count"]

        # Guard against a division by 0
        if total < 1:
            total = 1

        self.grants_percentage = self.count / total

        # Return conditions

        if test_class_type == TestType.QUALITY_TEST_CLASS:
            return self.count

        if self.aggregates["count"] == 1 and self.count == 1:
            self.grants_percentage = 1.0
            return f"1 {self.relevant_grant_type}".strip()

        if self.count <= 5:
            return f"{self.count} {self.relevant_grant_type}".strip()

        return f"{round(self.grants_percentage*100)}% of {self.relevant_grant_type}".strip()

    def format_heading_count(self, message, test_class_type=None, verb="have"):
        """Build a string with count of grants plus message

        The grant count phrase for the test is pluralized and
        prepended to message, eg: 1 grant has + message,
        2 grants have + message or 3 grants contain + message.
        """
        noun = "grant" if self.count == 1 else "grants"

        # Positive result  - "what is working well"
        # Avoid double negative
        if not message.startswith("not have") and message.startswith("not") and self.count == 0:
            message = message[len("not"):]
        if message.startswith("not have") and self.count == 0:
            verb = "do"
        # End positive result flip

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
