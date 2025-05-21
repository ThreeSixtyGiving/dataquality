from lib360dataquality.cove.threesixtygiving import (
    TEST_CLASSES,
)

from lib360dataquality.additional_test import TestType


def run_check(check):
    test = check(
        grants={"grants": []}, aggregates={"count": 2, "recipient_individuals_count": 0}
    )
    test.process(grant={"id": "moo"}, path_prefix="/")
    test.count = 2
    test.grants_percentage = 0.5

    message = test.produce_message()
    print(test.__class__.__name__)
    print(f" - Heading: {message['heading']}")
    print(f" - Message: {message['message']}")
    print("\n")


def main():
    """Extract and print out the error messages from the different classes of additional checks"""
    print("----------- Quality Tests ----------")
    for check in TEST_CLASSES[TestType.QUALITY_TEST_CLASS]:
        run_check(check)

    print("----------- Usefulness Tests -------")
    for check in TEST_CLASSES[TestType.USEFULNESS_TEST_CLASS]:
        run_check(check)


if __name__ == "__main__":
    main()
