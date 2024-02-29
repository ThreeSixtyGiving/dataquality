import os
from datetime import datetime
from django.urls import reverse_lazy

import pytest
import time
from cove.input.models import SuppliedData
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile

from lib360dataquality.cove.schema import Schema360
from lib360dataquality.cove.threesixtygiving import get_grants_aggregates, run_extra_checks, extend_numbers, spreadsheet_style_errors_table, TEST_CLASSES

# Source is cove_360/fixtures/fundingproviders-grants_fixed_2_grants.json
# see cove_360/fixtures/SOURCES for more info.
# Data has been edited to increase test coverage, so should not be used for
# anything besides testing.

current_year = datetime.now().year
current_month = datetime.now().month

GRANTS = {
    'grants': [{'Co-applicant(s)': 'Miss Hypatia Alexandria, Mr Thomas Aquinas',
                'Full name of applicant': 'Miss Jane Roe',
                'Grant number': '000001/X/00/X',
                'Grant type': 'Large Awards bob@bop.com',
                'Sponsor(s)': ' ',
                'Surname of applicant': 'Roe',
                'amountAwarded': 0,
                'awardDate': '{}-07-24'.format(current_year + 1),
                'currency': 'GBP',
                "beneficiaryLocation": [{
                    "name": "Bloomsbury",
                    "geoCodeType": "LONB"
                }],
                'dateModified': '13-03-2015',
                'fundingOrganization': [{'id': 'XSFAFA',
                                         'name': 'Funding Providers UK'}],
                'id': '360G-fundingproviders-000001/X/00/X',
                'plannedDates': [{
                    'startDate': '{}-10-01'.format(current_year),
                    'endDate': '{}-07-15T15:00:00Z'.format(current_year),
                    'duration': '30'
                }],
                'recipientOrganization': [{'addressLocality': 'London',
                                           'location': [{
                                               'name': 'Somewhere in London',
                                               'geoCode': 'W06000016'}],
                                           'charityNumber': '12345',
                                           'companyNumber': 'AAA',
                                           'id': '360G-Blah',
                                           'name': 'Company Name Limited'}],
                'classifications': [{
                    'title': 'Classification title'}],
                'title': 'Title A.  ,moo@moo.com '},
               {'Co-applicant(s)': ' ',
                'Department': 'Department of Studies',
                'Full name of applicant': 'Prof John Doe',
                'Grant number': '000002/X/00/X',
                'Grant type': 'Large Awards',
                'Sponsor(s)': ' ',
                'Surname of applicant': 'Doe',
                'amountAwarded': 178990,
                'awardDate': '{}-07-24'.format(current_year + 1),
                'currency': 'GBP',
                'dataSource': 'http://www.fundingproviders.co.uk/grants/',

                'description': 'Description for project A',
                'fundingOrganization': [{'id': '360G-CHC-000001',
                                         'name': 'Funding Providers UK'}],
                'grantProgramme': [{'code': 'AAC',
                                    'title': 'Awards Funding Committee'}],
                'id': '360G-fundingproviders-000002/X/00/X',
                'plannedDates': [{
                    'startDate': '{}-04-01'.format(current_year),
                    'endDate': '{}-10-23'.format(current_year + 13),
                    'duration': '25'
                }],
                'actualDates': [{
                    'startDate': '{}-10-01'.format(current_year + 1),
                    'endDate': '{}-04-23'.format(current_year),
                }],
                'recipientOrganization': [{'addressLocality': 'Leicester ',
                                           'location': [{
                                               'geoCodeType': 'UA',
                                               'name': 'Rhondda Cynon Taf',
                                               'geoCode': 'W06000016'}],
                                           'charityNumber': '1234567',
                                           'companyNumber': 'RC000000',
                                           'id': 'GB-UNKNOW-RC000000',
                                           'name': 'University of UK'}],
                'title': ('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do '
                          'eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut '
                          'enim ad minim veniam, quis nostrud exercitation ullamco laboris.')},
               {'Co-applicant(s)': ' ',
                'Department': 'Department of Studies',
                'Full name of applicant': 'Prof John Doe',
                'Grant number': '00002/X/00/X',
                'Grant type': 'Large Awards',
                'Sponsor(s)': ' ',
                'Surname of applicant': 'Doe',
                'amountAwarded': 178990,
                'awardDate': '{}-{}-01'.format(current_year, current_month),
                'currency': 'GBP',
                "beneficiaryLocation": [{
                    "name": "Gateshed",
                    "geoCodeType": "MD",
                    "geoCode": "E08000037",

                }],
                'dateModified': '13-03-2015',
                'description': 'Excepteur sint occaecat cupidatat non proident, sunt in culpa '
                               'qui officia deserunt mollit anim id est laborum.',
                'fundingOrganization': [{'id': 'GB-COH-000000',
                                         'name': 'Funding Providers UK'}],
                'grantProgramme': [{'code': 'AAC',
                                    'title': 'Arts Awards Funding Committee'}],
                'id': '360G-fundingproviders-000003/X/00/X',
                'plannedDates': [{
                    'startDate': '{}-02-30'.format(current_year + 1),
                    'endDate': '{}-03-29'.format(current_year + 2),
                    'duration': '25'
                }],
                'actualDates': [{
                    'startDate': '{}-03-29'.format(current_year - 26),
                    'endDate': '{}-04-29'.format(current_year + 6),
                }],
                'recipientOrganization': [{'addressLocality': 'Leicester ',
                                           'id': 'GB-CHC-00001',
                                           'name': 'University of UK',
                                           'postalCode': 'SW10 0AB'}],
                'relatedActivity': ["", "360G-xxx"],
                'title': 'Excepteur sint occaecat cupidatat non proident, sunt in culpa '
                         'qui officia deserunt mollit anim id est laborum.'}]}


# To output the GRANTS data for testing:
#import json
#with open("test_data.json", "w+") as f:
#   json.dump(GRANTS, f, indent=2)


SOURCE_MAP = {
    'grants/0': [['grants', 2]],
    'grants/0/Co-applicant(s)': [['grants', 'E', 2, 'Co-applicant(s)']],
    'grants/0/Full name of applicant': [['grants',
                                         'D',
                                         2,
                                         'Full name of applicant']],
    'grants/0/Grant number': [['grants', 'B', 2, 'Grant number']],
    'grants/0/Grant type': [['grants', 'G', 2, 'Grant type']],
    'grants/0/Sponsor(s)': [['grants', 'F', 2, 'Sponsor(s)']],
    'grants/0/Surname of applicant': [['grants', 'C', 2, 'Surname of applicant']],
    'grants/0/amountAwarded': [['grants', 'Q', 2, 'Amount Awarded']],
    'grants/0/awardDate': [['grants', 'S', 2, 'Award Date']],
    'grants/0/currency': [['grants', 'R', 2, 'Currency']],
    'grants/0/beneficiaryLocation': [['grants', 'AA', 2, 'Beneficiary Location']],
    'grants/0/dataSource': [['grants', 'Y', 2, 'Data source']],
    'grants/0/dateModified': [['grants', 'X', 2, 'Last modified']],
    'grants/0/fundingOrganization/0': [['grants', 2]],
    'grants/0/fundingOrganization/0/id': [['grants',
                                           'V',
                                           2,
                                           'Funding Org:Identifier']],
    'grants/0/fundingOrganization/0/name': [['grants',
                                             'W',
                                             2,
                                             'Funding Org:Name']],
    'grants/0/id': [['grants', 'A', 2, 'Identifier']],
    'grants/0/plannedDates/0': [['grants', 2]],
    'grants/0/plannedDates/0/startDate': [['grants',
                                          '',
                                          2,
                                          'Planned Dates:Start Date']],
    'grants/0/plannedDates/0/endDate': [['grants',
                                         '',
                                         2,
                                         'Planned Dates:End Date']],
    'grants/0/plannedDates/0/duration': [['grants',
                                          'P',
                                          2,
                                          'Planned Dates:Duration (months)']],
    'grants/0/recipientOrganization/0': [['grants', 2]],
    'grants/0/recipientOrganization/0/addressLocality': [['grants',
                                                          'N',
                                                          2,
                                                          'Recipient Org:City']],
    'grants/0/recipientOrganization/0/charityNumber': [['grants',
                                                        'M',
                                                        2,
                                                        'Recipient Org:Charity '
                                                        'Number']],
    'grants/0/recipientOrganization/0/companyNumber': [['grants',
                                                        'L',
                                                        2,
                                                        'Recipient Org:Company '
                                                        'Number']],
    'grants/0/recipientOrganization/0/id': [['grants',
                                             'J',
                                             2,
                                             'Recipient Org:Identifier']],
    'grants/0/recipientOrganization/0/name': [['grants',
                                               'K',
                                               2,
                                               'Recipient Org:Name']],
    'grants/0/title': [['grants', 'O', 2, 'Title']],
    'grants/1': [['grants', 3]],
    'grants/1/Co-applicant(s)': [['grants', 'E', 3, 'Co-applicant(s)']],
    'grants/1/Department': [['grants', 'H', 3, 'Department']],
    'grants/1/Full name of applicant': [['grants',
                                         'D',
                                         3,
                                         'Full name of applicant']],
    'grants/1/Grant number': [['grants', 'B', 3, 'Grant number']],
    'grants/1/Grant type': [['grants', 'G', 3, 'Grant type']],
    'grants/1/Sponsor(s)': [['grants', 'F', 3, 'Sponsor(s)']],
    'grants/1/Surname of applicant': [['grants', 'C', 3, 'Surname of applicant']],
    'grants/1/amountAwarded': [['grants', 'Q', 3, 'Amount Awarded']],
    'grants/1/awardDate': [['grants', 'S', 3, 'Award Date']],
    'grants/1/currency': [['grants', 'R', 3, 'Currency']],
    'grants/1/dataSource': [['grants', 'Y', 3, 'Data source']],
    'grants/1/dateModified': [['grants', 'X', 3, 'Last modified']],
    'grants/1/description': [['grants', 'Z', 3, 'Description']],
    'grants/1/fundingOrganization/0': [['grants', 3]],
    'grants/1/fundingOrganization/0/id': [['grants',
                                           'V',
                                           3,
                                           'Funding Org:Identifier']],
    'grants/1/fundingOrganization/0/name': [['grants',
                                             'W',
                                             3,
                                             'Funding Org:Name']],
    'grants/1/grantProgramme/0': [['grants', 3]],
    'grants/1/grantProgramme/0/code': [['grants', 'T', 3, 'Grant Programme:Code']],
    'grants/1/grantProgramme/0/title': [['grants',
                                         'U',
                                         3,
                                         'Grant Programme:Title']],
    'grants/1/id': [['grants', 'A', 3, 'Identifier']],
    'grants/1/plannedDates/0': [['grants', 3]],
    'grants/1/plannedDates/0/startDate': [['grants',
                                           '',
                                           3,
                                           'Planned Dates:Start Date']],
    'grants/1/plannedDates/0/endDate': [['grants',
                                         '',
                                         3,
                                         'Planned Dates:End Date']],
    'grants/1/plannedDates/0/duration': [['grants',
                                          'P',
                                          3,
                                          'Planned Dates:Duration (months)']],
    'grants/1/actualDates/0/startDate': [['grants',
                                          '',
                                          3,
                                          'Planned Dates:Start Date']],
    'grants/1/actualDates/0/endDate': [['grants',
                                        '',
                                        3,
                                        'Planned Dates:End Date']],
    'grants/1/recipientOrganization/0': [['grants', 3]],
    'grants/1/recipientOrganization/0/addressLocality': [['grants',
                                                          'N',
                                                          3,
                                                          'Recipient Org:City']],
    'grants/1/recipientOrganization/0/charityNumber': [['grants',
                                                        'M',
                                                        3,
                                                        'Recipient Org:Charity '
                                                        'Number']],
    'grants/1/recipientOrganization/0/companyNumber': [['grants',
                                                        'L',
                                                        3,
                                                        'Recipient Org:Company '
                                                        'Number']],
    'grants/1/recipientOrganization/0/id': [['grants',
                                             'J',
                                             3,
                                             'Recipient Org:Identifier']],
    'grants/1/recipientOrganization/0/name': [['grants',
                                               'K',
                                               3,
                                               'Recipient Org:Name']],
    'grants/1/title': [['grants', 'O', 3, 'Title']],
    'grants/2': [['grants', 4]],
    'grants/2/Co-applicant(s)': [['grants', 'E', 4, 'Co-applicant(s)']],
    'grants/2/Department': [['grants', 'H', 4, 'Department']],
    'grants/2/Full name of applicant': [['grants',
                                         'D',
                                         4,
                                         'Full name of applicant']],
    'grants/2/Grant number': [['grants', 'B', 4, 'Grant number']],
    'grants/2/Grant type': [['grants', 'G', 4, 'Grant type']],
    'grants/2/Sponsor(s)': [['grants', 'F', 4, 'Sponsor(s)']],
    'grants/2/Surname of applicant': [['grants', 'C', 4, 'Surname of applicant']],
    'grants/2/amountAwarded': [['grants', 'Q', 4, 'Amount Awarded']],
    'grants/2/awardDate': [['grants', 'S', 4, 'Award Date']],
    'grants/2/currency': [['grants', 'R', 4, 'Currency']],
    'grants/2/dataSource': [['grants', 'Y', 4, 'Data source']],
    'grants/2/dateModified': [['grants', 'X', 4, 'Last modified']],
    'grants/2/description': [['grants', 'Z', 4, 'Description']],
    'grants/2/fundingOrganization/0': [['grants', 4]],
    'grants/2/fundingOrganization/0/id': [['grants',
                                           'V',
                                           4,
                                           'Funding Org:Identifier']],
    'grants/2/fundingOrganization/0/name': [['grants',
                                             'W',
                                             4,
                                             'Funding Org:Name']],
    'grants/2/grantProgramme/0': [['grants', 4]],
    'grants/2/grantProgramme/0/code': [['grants', 'T', 4, 'Grant Programme:Code']],
    'grants/2/grantProgramme/0/title': [['grants',
                                         'U',
                                         4,
                                         'Grant Programme:Title']],
    'grants/2/id': [['grants', 'A', 4, 'Identifier']],
    'grants/2/plannedDates/0': [['grants', 4]],
    'grants/2/plannedDates/0/startDate': [['grants',
                                          '',
                                          4,
                                          'Planned Dates:Start Date']],
    'grants/2/plannedDates/0/endDate': [['grants',
                                         '',
                                         4,
                                         'Planned Dates:End Date']],
    'grants/2/plannedDates/0/duration': [['grants',
                                          'P',
                                          4,
                                          'Planned Dates:Duration (months)']],
    'grants/2/actualDates/0/startDate': [['grants',
                                          '',
                                          4,
                                          'Actual Dates:Start Date']],
    'grants/2/actualDates/0/endDate': [['grants',
                                        '',
                                        4,
                                        'Actual Dates:End Date']],
    'grants/2/recipientOrganization/0': [['grants', 4]],
    'grants/2/recipientOrganization/0/addressLocality': [['grants',
                                                          'N',
                                                          4,
                                                          'Recipient Org:City']],
    'grants/2/recipientOrganization/0/charityNumber': [['grants',
                                                        'M',
                                                        4,
                                                        'Recipient Org:Charity '
                                                        'Number']],
    'grants/2/recipientOrganization/0/companyNumber': [['grants',
                                                        'L',
                                                        4,
                                                        'Recipient Org:Company '
                                                        'Number']],
    'grants/2/recipientOrganization/0/id': [['grants',
                                             'J',
                                             4,
                                             'Recipient Org:Identifier']],
    'grants/2/recipientOrganization/0/name': [['grants',
                                               'K',
                                               4,
                                               'Recipient Org:Name']],
    'grants/2/title': [['grants', 'O', 4, 'Title']]
}

TOTAL_GRANTS = len(GRANTS["grants"])

QUALITY_ACCURACY_CHECKS_RESULTS = [
    (
        {
            "heading": "1 grant has a value of £0",
            "message": "It’s worth taking a look at these grants and deciding if they should be included in your data. It’s unusual to have grants of £0, but there may be a reasonable explanation. If £0 value grants are to be published in your data consider adding an explanation to the description of the grant to help anyone using the data to understand how to interpret the information.",
            "type": "ZeroAmountTest",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/0/amountAwarded"],
        [
            {
                "sheet": "grants",
                "letter": "Q",
                "row_number": 2,
                "header": "Amount Awarded",
            }
        ],
    ),
    (
        {
            "heading": '1 grant has a <span class="highlight-background-text">Funding Org:Identifier</span> that does not draw from a recognised register',
            "message": 'In the 360Giving Data Standard, organisation identifiers have two parts: an identifier and a prefix which describes the list the identifier is taken from. This error notice is caused by the prefix in an organisation identifier not being taken from a recognised register from the <a target=\"_blank\" href="https://org-id.guide/">org-id list locator</a>. See our <a target=\"_blank\" href="https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier">guidance on organisation identifiers</a> for further help.',
            "type": "FundingOrgUnrecognisedPrefix",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/0/fundingOrganization/0/id"],
        [
            {
                "sheet": "grants",
                "letter": "V",
                "row_number": 2,
                "header": "Funding Org:Identifier",
            }
        ],
    ),
    (
        {
            "heading": '1 grant has a <span class="highlight-background-text">Recipient Org:Identifier</span> that does not draw from a recognised register',
            "message": 'In the 360Giving Data Standard, organisation identifiers have two parts: an identifier and a prefix which describes the list the identifier is taken from. This error notice is caused by the prefix in an organisation identifier not being taken from a recognised register from the <a target=\"_blank\" href="https://org-id.guide/">org-id list locator</a>. See our <a target=\"_blank\" href="https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier">guidance on organisation identifiers</a> for further help.',
            "type": "RecipientOrgUnrecognisedPrefix",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/1/recipientOrganization/0/id"],
        [
            {
                "sheet": "grants",
                "letter": "J",
                "row_number": 3,
                "header": "Recipient Org:Identifier",
            }
        ],
    ),
    (
        {
            "heading": '1 grant has a value provided in the <span class="highlight-background-text">Recipient Org:Charity Number</span> column that doesn’t look like a UK charity number',
            "message": 'Common causes of this error notice are missing or extra digits, typos or incorrect values such as text appearing in this field. You can check UK charity numbers online at <a target=\"_blank\" href="https://findthatcharity.uk/">FindthatCharity</a>. This error may also be triggered by correctly formatted non-UK charity numbers, in which case this message can be ignored.',
            "type": "RecipientOrgCharityNumber",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/0/recipientOrganization/0/charityNumber"],
        [
            {
                "sheet": "grants",
                "letter": "M",
                "row_number": 2,
                "header": "Recipient Org:Charity Number",
            }
        ],
    ),
    (
        {
            "heading": '1 grant has a value provided in the <span class="highlight-background-text">Recipient Org:Company Number</span> column that doesn’t look like a company number',
            "message": 'Common causes of this error notice are missing or extra digits, typos or incorrect values such as text appearing in this field. UK Company numbers are typically 8 digits, for example <span class="highlight-background-text">09876543</span> or sometimes start with a 2 letter prefix, <span class="highlight-background-text">SC123459</span>. You can check company numbers online at <a target=\"_blank\" href="https://find-and-update.company-information.service.gov.uk/">Companies House</a>. This error may also be triggered by correctly formatted non-UK company numbers, in which case this message can be ignored.',
            "type": "RecipientOrgCompanyNumber",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/0/recipientOrganization/0/companyNumber"],
        [
            {
                "sheet": "grants",
                "letter": "L",
                "row_number": 2,
                "header": "Recipient Org:Company Number",
            }
        ],
    ),
    (
        {
            "heading": "2 grants have a Funding or Recipient Organisation identifier that might not be valid",
            "message": "The identifiers might not be valid for the recognised register that they refer to - for example, an identifier with the prefix 'GB-CHC' that contains an invalid charity number. Common causes of this are missing or extra digits, typos or incorrect values such as text appearing in this field. See our <a target=\"_blank\" href=\"https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier\">guidance on organisation identifiers</a> for further help.",
            "type": "OrganizationIdLooksInvalid",
            "count": 2,
            "percentage": 2/TOTAL_GRANTS
        },
        ["grants/2/fundingOrganization/0/id", "grants/2/recipientOrganization/0/id"],
        [
            {
                "sheet": "grants",
                "letter": "V",
                "row_number": 4,
                "header": "Funding Org:Identifier",
            },
            {
                "sheet": "grants",
                "letter": "J",
                "row_number": 4,
                "header": "Recipient Org:Identifier",
            },
        ],
    ),
    (
        {
            "heading": "3 different funding organisation identifiers listed",
            "message": 'If you are only publishing for a single funder then you should review your <span class="highlight-background-text">Funding Organisation identifier</span> field to see where multiple IDs have occurred. If you are expecting to be publishing data for multiple funders and the number of funders is correct, then you can ignore this error notice.',
            "type": "MoreThanOneFundingOrg",
            "count": 0,
            "percentage": 0
        },
        [
            "grants/0/fundingOrganization/0/id",
            "grants/1/fundingOrganization/0/id",
            "grants/2/fundingOrganization/0/id",
        ],
        [
            {
                "sheet": "grants",
                "letter": "V",
                "row_number": 2,
                "header": "Funding Org:Identifier",
            },
            {
                "sheet": "grants",
                "letter": "V",
                "row_number": 3,
                "header": "Funding Org:Identifier",
            },
            {
                "sheet": "grants",
                "letter": "V",
                "row_number": 4,
                "header": "Funding Org:Identifier",
            },
        ],
    ),
    (
        {
            "heading": "2 grants contain text that looks like an email address",
            "message": "Your data may contain an email address (or something that looks like one), which can constitute personal data if it is the email of an individual. The use and distribution of personal data is restricted by the Data Protection Act. You should ensure that any personal data is removed from your data prior to publishing it, or that it is only included with the knowledge and consent of the person to whom it refers.",
            "type": "LooksLikeEmail",
            "count": 2,
            "percentage": 2/TOTAL_GRANTS
        },
        ["grants/0/Grant type", "grants/0/title"],
        [
            {"sheet": "grants", "letter": "G", "row_number": 2, "header": "Grant type"},
            {"sheet": "grants", "letter": "O", "row_number": 2, "header": "Title"},
        ],
    ),
    (
        {
            "heading": "1 grant has dates that don’t exist",
            "message": "Your data contains dates that didn't, or won't, exist - such as the 31st of September, or the 29th of February in a year that's not a leap year. This error is commonly caused by typos during data entry.",
            "type": "ImpossibleDates",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/2/plannedDates/0/startDate"],
        [
            {
                "sheet": "grants",
                "letter": "",
                "row_number": 4,
                "header": "Planned Dates:Start Date",
            }
        ],
    ),
    (
        {
            "heading": '1 grant has <span class="highlight-background-text">Planned Dates:Start Date</span> entries that are after the corresponding <span class="highlight-background-text">Planned Dates:End Date</span>',
            "message": "This can happen when the fields are accidentally reversed, or if there is a typo in the date. This can also be caused by inconsistent date formatting when data was prepared using spreadsheet software.",
            "type": "PlannedStartDateBeforeEndDate",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/0/plannedDates/0/startDate"],
        [
            {
                "sheet": "grants",
                "letter": "",
                "row_number": 2,
                "header": "Planned Dates:Start Date",
            }
        ],
    ),
    (
        {
            "heading": '1 grant has <span class="highlight-background-text">Actual Dates:Start Date</span> entries that are after the corresponding <span class="highlight-background-text">Actual Dates:End Date</span>',
            "message": "This can happen when the fields are accidentally reversed, or if there is a typo in the date. This can also be caused by inconsistent date formatting when data was prepared using spreadsheet software.",
            "type": "ActualStartDateBeforeEndDate",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/1/actualDates/0/startDate"],
        [
            {
                "sheet": "grants",
                "letter": "",
                "row_number": 3,
                "header": "Planned Dates:Start Date",
            }
        ],
    ),
    (
        {
            "heading": "1 grant has Planned Dates that are over 12 years in the future",
            "message": "Your data contains Planned Dates that are more than 12 years into the future. You can disregard this error notice if your data describes activities that run a long time into the future, but you should check for data entry errors if this isn't expected.",
            "type": "FarFuturePlannedDates",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/1/plannedDates/0/endDate"],
        [
            {
                "sheet": "grants",
                "letter": "",
                "row_number": 3,
                "header": "Planned Dates:End Date",
            }
        ],
    ),
    (
        {
            "heading": "1 grant has Actual Date entries that are over 5 years in the future",
            "message": "Your data contains Actual Date entries that are more than 5 years into the future. You can disregard this error notice if your data describes activities far in the future, but you should check for data entry errors if this isn't expected.",
            "type": "FarFutureActualDates",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/2/actualDates/0/endDate"],
        [
            {
                "sheet": "grants",
                "letter": "",
                "row_number": 4,
                "header": "Actual Dates:End Date",
            }
        ],
    ),
    (
        {
            "heading": "1 grant has dates that are over 25 years ago",
            "message": "Your data contains dates that are more than 25 years ago. You can disregard this error notice if your data is about activities far in the past, but you should check for data entry errors if this isn't expected.",
            "type": "FarPastDates",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS
        },
        ["grants/2/actualDates/0/startDate"],
        [
            {
                "sheet": "grants",
                "letter": "",
                "row_number": 4,
                "header": "Actual Dates:Start Date",
            }
        ],
    ),
    (
        {
            "heading": "2 grants have Award Dates that are in the future",
            "message": "Your data contains grant Award Dates in the future. This date is when the decision to award the grant was made so it would normally be in the past. This error can happen when there is a typo in the date, or the data includes grants that are not yet fully committed",
            "type": "PostDatedAwardDates",
            "count": 2,
            "percentage": 2/TOTAL_GRANTS
        },
        ["grants/0/awardDate", "grants/1/awardDate"],
        [
            {"sheet": "grants", "letter": "S", "row_number": 2, "header": "Award Date"},
            {"sheet": "grants", "letter": "S", "row_number": 3, "header": "Award Date"},
        ],
    ),
]


USEFULNESS_CHECKS_RESULTS = [
    (
        {
            "heading": "1 recipient organisation grant has a <span class=\"highlight-background-text\">Recipient Org:Identifier</span> that starts '360G-'",
            "message": 'Use an external reference, such as a charity or company number, to identify an organisation whenever possible. Doing so makes it possible to see when recipients have received grants from multiple funders, and allows grants data to be linked or combined with information from official registers. Some organisations, such as small unregistered groups, do not have an official registration number that can be used. In these cases the organisation identifier should start ‘360G-‘ and use an identifier taken from the publisher’s internal systems. See our <a target=\"_blank\" href="https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier">guidance on organisation identifiers</a> for further help.',
            "type": "RecipientOrg360GPrefix",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS,
        },
        ["grants/0/recipientOrganization/0/id"],
        [
            {
                "sheet": "grants",
                "letter": "J",
                "row_number": 2,
                "header": "Recipient Org:Identifier",
            }
        ],
    ),
    (
        {
            "heading": "1 grant has a <span class=\"highlight-background-text\">Funding Org:Identifier</span> that starts '360G-'",
            "message": 'Use an external reference, such as a charity or company number, to identify a funding organisation whenever possible. Some funders do not have an official registration number that can be used. In these cases the funding organisation identifier should reuse the publisher prefix and therefore start with “360G-”. See our <a target=\"_blank\" href="https://standard.threesixtygiving.org/en/latest/technical/identifiers/#organisation-identifier">guidance on organisation identifiers</a> for further help.',
            "type": "FundingOrg360GPrefix",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS,
        },
        ["grants/1/fundingOrganization/0/id"],
        [
            {
                "sheet": "grants",
                "letter": "V",
                "row_number": 3,
                "header": "Funding Org:Identifier",
            }
        ],
    ),
    (
        {
            "heading": '1 recipient organisation grant does not have either a <span class="highlight-background-text">Recipient Org:Company Number</span> or a <span class="highlight-background-text">Recipient Org:Charity Number</span>',
            "message": "Company and charity numbers are important for understanding grantmaking in the UK and including these separately makes it easier for users to match grants data with official sources of information about the recipients. If your grants are to organisations that don’t have UK Company or UK Charity numbers, you can ignore this notice.",
            "type": "NoRecipientOrgCompanyCharityNumber",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS,
        },
        ["grants/2/recipientOrganization/0/id"],
        [
            {
                "sheet": "grants",
                "letter": "J",
                "row_number": 4,
                "header": "Recipient Org:Identifier",
            }
        ],
    ),
    (
        {
            "heading": "1 recipient organisation grant does not have recipient organisation location information",
            "message": 'Recipient location data in the form of postcodes or geocodes provides a consistent way to describe a location. This data can be used to produce maps, such as the maps in <a target=\"_blank\" href="https://insights.threesixtygiving.org/">360Insights</a>, showing the geographical distribution of funding and allows grants data to be looked at alongside official statistics, such as the Indices of multiple deprivation. See our <a target=\"_blank\" href="https://standard.threesixtygiving.org/en/latest/guidance/location-guide/">guidance on location data</a> for further help. ',
            "type": "IncompleteRecipientOrg",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS,

        },
        ["grants/0/recipientOrganization/0/id"],
        [
            {
                "sheet": "grants",
                "letter": "J",
                "row_number": 2,
                "header": "Recipient Org:Identifier",
            }
        ],
    ),
    (
        {
            "heading": '1 grant does not contain any <span class="highlight-background-text">Grant Programme</span> fields',
            "message": "Grant programme names help users to understand a funder’s different types of funding and priorities, and see how their grants vary across and within these. This information is especially useful when it refers to the communities, sectors, issues or places that are the focus of the programme. If your organisation does not have grant programmes this notice can be ignored.",
            "type": "NoGrantProgramme",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS,
        },
        ["grants/0/id"],
        [{"sheet": "grants", "letter": "A", "row_number": 2, "header": "Identifier"}],
    ),
    (
        {
            "heading": "1 grant does not contain any beneficiary location fields",
            "message": 'Beneficiary location data in the form of place names and geocodes allow users to understand which places funding is reaching. This data can be more accurate in showing where grants are going geographically, especially in cases where the recipient location is in a different place from the activity being funded. Beneficiary location codes can be used to produce maps, such as the ones in <a target=\"_blank\" href="https://insights.threesixtygiving.org/">360Insights</a>, showing the geographical distribution of funding and allows grants data to be looked at alongside official statistics, such as the Indices of multiple deprivation. See our <a target=\"_blank\" href="https://standard.threesixtygiving.org/en/latest/guidance/location-guide/">guidance on location data </a>for further help.',
            "type": "NoBeneficiaryLocation",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS,
        },
        ["grants/1/id"],
        [{"sheet": "grants", "letter": "A", "row_number": 3, "header": "Identifier"}],
    ),
    (
        {
            "heading": "1 grant has a title and a description that are the same",
            "message": "Users may find that the data is less useful as they are unable to discover more about the grants. Consider including a more detailed description if you have one.",
            "type": "TitleDescriptionSame",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS,
        },
        ["grants/2/description"],
        [{"sheet": "grants", "letter": "Z", "row_number": 4, "header": "Description"}],
    ),
    (
        {
            "heading": "1 grant has a title that is longer than recommended",
            "message": "Titles for grant activities should be under 140 characters long so that people can quickly understand the purpose of the grant.",
            "type": "TitleLength",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS,
        },
        ["grants/1/title"],
        [{"sheet": "grants", "letter": "O", "row_number": 3, "header": "Title"}],
    ),
    (
        {
            "heading": '1 grant does not have <span class="highlight-background-text">Last Modified</span> information',
            "message": '<span class="highlight-background-text">Last Modified</span> shows the date and time when information about a grant was last updated in your file. Including this information allows data users to see when changes have been made and reconcile differences between versions of your data.',
            "type": "NoLastModified",
            "count": 1,
            "percentage": 1/TOTAL_GRANTS,
        },
        ["grants/1/id"],
        [{"sheet": "grants", "letter": "A", "row_number": 3, "header": "Identifier"}],
    ),
    (
        {
            "heading": '2 grants do not have <span class="highlight-background-text">Data Source</span> information',
            "message": '<span class="highlight-background-text">Data Source</span> is a web link pointing to the source of this data. It informs users about where information came from and is an important part of establishing trust in your data. This may be a link to an original 360Giving data file, a file from which the data was converted, or your organisation’s website.',
            "type": "NoDataSource",
            "count": 2,
            "percentage": 2/TOTAL_GRANTS,
        },
        ["grants/0/id", "grants/2/id"],
        [
            {"sheet": "grants", "letter": "A", "row_number": 2, "header": "Identifier"},
            {"sheet": "grants", "letter": "A", "row_number": 4, "header": "Identifier"},
        ],
    ),
]


@pytest.mark.parametrize('json_data', [
    # A selection of JSON strings we expect to give a 200 status code, even
    # though some of them aren't valid 360
    'true',
    'null',
    '1',
    '{}',
    '[]',
    '[[]]',
    '{"grants": {}}',
    '{"grants" : 1.0}',
    '{"grants" : 2}',
    '{"grants" : true}',
    '{"grants" : "test"}',
    '{"grants" : null}',
    '{"grants" : {"a":"b"}}',
    '{"grants" : [["test"]]}',
])
@pytest.mark.django_db
def test_explore_page(client, json_data):
    data = SuppliedData.objects.create()
    data.original_file.save('test.json', ContentFile(json_data))
    data.current_app = 'cove_360'
    resp = client.get(reverse_lazy('results', args=[data.pk]))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_explore_page_convert(client):
    data = SuppliedData.objects.create()
    data.original_file.save('test.json', ContentFile('{}'))
    data.current_app = 'cove_360'
    resp = client.get(reverse_lazy('results', args=[data.pk]))
    time.sleep(1)
    assert resp.status_code == 200
    assert resp.context['conversion'] == 'flattenable'

    # Check that what the repr of our SuppliedData object looks like
    assert 'SuppliedData' in repr(data)
    assert 'test.json' in repr(data)

    resp = client.post(data.get_absolute_url(), {'flatten': 'true'}, follow=True)
    assert resp.status_code == 200
    assert resp.context['conversion'] == 'flatten'
    assert 'converted_file_size' in resp.context
    assert 'converted_file_size_titles' in resp.context


@pytest.mark.django_db
def test_explore_page_csv(client):
    data = SuppliedData.objects.create()
    data.original_file.save('test.csv', ContentFile('a,b'))
    resp = client.get(reverse_lazy('results', args=[data.pk]))
    assert resp.status_code == 200
    assert resp.context['conversion'] == 'unflatten'
    assert resp.context['converted_file_size'] == 20


@pytest.mark.django_db
def test_explore_not_json(client):
    data = SuppliedData.objects.create()
    with open(os.path.join('cove_360', 'fixtures', 'fundingproviders-grants_malformed.json')) as fp:
        data.original_file.save('test.json', UploadedFile(fp))
    resp = client.get(reverse_lazy('results', args=[data.pk]))
    assert resp.status_code == 200
    assert b'not well formed JSON' in resp.content


@pytest.mark.django_db
def test_explore_unconvertable_spreadsheet(client):
    data = SuppliedData.objects.create()
    with open(os.path.join('cove_360', 'fixtures', 'bad.xlsx'), 'rb') as fp:
        data.original_file.save('basic.xlsx', UploadedFile(fp))
    resp = client.get(reverse_lazy('results', args=[data.pk]))
    assert resp.status_code == 200
    assert b'We think you tried to supply a spreadsheet, but we failed to convert it.' in resp.content


# Suggested method of updating test_quality_accuracy/test_usefulness_checks data
# in each function save the output:
#  with open("/tmp/update_test_data.txt", "w+") as f:
#    f.write(str(a))
# Then use python-black to format the text file and paste the result to  QUALITY_ACCURACY_CHECKS_RESULTS
# and USEFULNESS_CHECKS_RESULTS respectively.

def test_quality_accuracy_checks():
    aggregates = get_grants_aggregates(GRANTS, ignore_errors=True)
    test_result = run_extra_checks(GRANTS, SOURCE_MAP, TEST_CLASSES['quality_accuracy'], aggregates)

    assert test_result == QUALITY_ACCURACY_CHECKS_RESULTS


def test_usefulness_checks():
    aggregates = get_grants_aggregates(GRANTS, ignore_errors=True)
    test_result = run_extra_checks(GRANTS, SOURCE_MAP, TEST_CLASSES['usefulness'], aggregates)

    assert test_result == USEFULNESS_CHECKS_RESULTS


def test_extend_numbers():
    assert list(extend_numbers([2])) == [1, 2, 3]
    assert list(extend_numbers([4])) == [3, 4, 5]
    assert list(extend_numbers([4, 6])) == [3, 4, 5, 6, 7]
    assert list(extend_numbers([4, 7])) == [3, 4, 5, 6, 7, 8]
    assert list(extend_numbers([4, 8])) == [3, 4, 5, 7, 8, 9]
    assert list(extend_numbers([1])) == [1, 2]
    assert list(extend_numbers([4, 5, 6])) == [3, 4, 5, 6, 7]
    assert list(extend_numbers([4, 5, 7, 2001])) == [3, 4, 5, 6, 7, 8, 2000, 2001, 2002]


def ex(value):
    ''' Shorthand for value metadata with type `example`.'''
    return {'type': 'example', 'value': value}


def con(value):
    ''' Shorthand for value metadata with type `context`.'''
    return {'type': 'context', 'value': value}


@pytest.mark.django_db
def test_quality_check_email(client):
    '''
    Email fields (eg. Funding Org:Email or Recipient Org:Email) should not appear in `LooksLikeEmail` check.
    'fundingproviders-grants-email.json' contains three emails, two of them in emails fields.
    '''
    data = SuppliedData.objects.create()
    with open(os.path.join('cove_360', 'fixtures', 'fundingproviders-grants-email.json')) as fp:
        data.original_file.save('fundingproviders-grants-email.json', UploadedFile(fp))
    response = client.post(data.get_absolute_url(), {'flatten': 'true'}, follow=True)

    assert b'1 grant contains text that looks like an email address' in response.content


class FakeCell():
    def __init__(self, value):
        self.value = value

    def value(self, value):
        return self.value


class TestSpreadsheetErrorsTable():
    def test_single(self):
        assert spreadsheet_style_errors_table([
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'C',
                'value': 'a value',
            }
        ], None) == {
            'Sheet 1': [
                ['', 'C'],
                [5, {'type': 'example', 'value': 'a value'}],
            ]
        }

    def test_many1(self):
        assert spreadsheet_style_errors_table([
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'C',
                'value': 'value1',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'E',
                'value': 'value2',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 7,
                'col_alpha': 'E',
                'value': 'value3',
            },
            {
                'sheet': 'Sheet 2',
                'row_number': 11,
                'col_alpha': 'Q',
                'value': 'value4',
            },
        ], None) == {
            'Sheet 1': [
                ['', 'C', 'E'],
                [5, ex('value1'), ex('value2')],
                [7, con(''), ex('value3')],
            ]
        }

    def test_many2(self):
        assert spreadsheet_style_errors_table([
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'C',
                'value': 'value1',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'E',
                'value': 'value2',
            },
            {
                'sheet': 'Sheet 2',
                'row_number': 11,
                'col_alpha': 'Q',
                'value': 'value4',
            },
        ], None) == {
            'Sheet 1': [
                ['', 'C', 'E'],
                [5, ex('value1'), ex('value2')],
            ],
            'Sheet 2': [
                ['', 'Q'],
                [11, ex('value4')],
            ]
        }

    def test_extra_examples_visible(self):
        assert spreadsheet_style_errors_table([
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'C',
                'value': 'value1',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'E',
                'value': 'value2',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 7,
                'col_alpha': 'C',
                'value': 'value3',
            },
        ] + [{}] * 100 + [
            {
                'sheet': 'Sheet 1',
                'row_number': 7,
                'col_alpha': 'E',
                'value': 'value4',
            },
        ], None) == {
            'Sheet 1': [
                ['', 'C', 'E'],
                [5, ex('value1'), ex('value2')],
                [7, ex('value3'), ex('value4')],
            ]
        }

    def test_single_empty_workbook(self):
        assert spreadsheet_style_errors_table([
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'C',
                'value': 'val',
            }
        ], {'Sheet 1': {}}) == {
            'Sheet 1': [
                ['', 'B', 'C', 'D'],
                [1, con(''), con(''), con('')],
                [4, con(''), con(''), con('')],
                [5, con(''), ex('val'), con('')],
                [6, con(''), con(''), con('')],
            ]
        }

    def test_single_workbook(self):
        assert spreadsheet_style_errors_table([
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'C',
                'value': 'val',
            }
        ], {'Sheet 1': {
            'B1': FakeCell('v1H'),
            'B4': FakeCell('v11'),
            'B5': FakeCell('v12'),
            'B6': FakeCell('v13'),
            'C1': FakeCell('v2H'),
            'C4': FakeCell('v21'),
            # This value (C5) will be ignored in favour of the one
            # fromthe examples array above.
            'C5': FakeCell('v22'),
            'C6': FakeCell('v23'),
            'D1': FakeCell('v3H'),
            'D4': FakeCell('v31'),
            'D5': FakeCell('v32'),
            'D6': FakeCell('v33'),
        }}) == {
            'Sheet 1': [
                ['', 'B', 'C', 'D'],
                [1, con('v1H'), con('v2H'), con('v3H')],
                [4, con('v11'), con('v21'), con('v31')],
                [5, con('v12'), ex('val'), con('v32')],
                [6, con('v13'), con('v23'), con('v33')],
            ]
        }

    def test_extra_examples_visible_workbook(self):
        assert spreadsheet_style_errors_table([
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'C',
                'value': 'value1',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
                'col_alpha': 'E',
                'value': 'value2',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 7,
                'col_alpha': 'C',
                'value': 'value3',
            },
        ] + [{}] * 100 + [
            {
                'sheet': 'Sheet 1',
                'row_number': 7,
                'col_alpha': 'E',
                'value': 'value4',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 4,
                'col_alpha': 'C',
                'value': 'value5',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 6,
                'col_alpha': 'C',
                'value': 'value6',
            },
            {
                'sheet': 'Sheet 1',
                'row_number': 8,
                'col_alpha': 'C',
                'value': 'value7',
            },
        ], {'Sheet 1': {
            'B1': FakeCell('v1H'),
            'B4': FakeCell('v11'),
            'B5': FakeCell('v12'),
            'B6': FakeCell('v13'),
            'B7': FakeCell('v14'),
            'B8': FakeCell('v15'),
            'C1': FakeCell('v2H'),
            'C4': FakeCell('v21'),
            'C5': FakeCell('v22'),
            'C6': FakeCell('v23'),
            'C7': FakeCell('v24'),
            'C8': FakeCell('v25'),
            'D1': FakeCell('v3H'),
            'D4': FakeCell('v31'),
            'D5': FakeCell('v32'),
            'D6': FakeCell('v33'),
            'D7': FakeCell('v34'),
            'D8': FakeCell('v35'),
            'E1': FakeCell('v4H'),
            'E4': FakeCell('v41'),
            'E5': FakeCell('v42'),
            'E6': FakeCell('v43'),
            'E7': FakeCell('v44'),
            'E8': FakeCell('v45'),
            'F1': FakeCell('v5H'),
            'F4': FakeCell('v51'),
            'F5': FakeCell('v52'),
            'F6': FakeCell('v53'),
            'F7': FakeCell('v54'),
            'F8': FakeCell('v55'),
        }}) == {
            'Sheet 1': [
                ['', 'B', 'C', 'D', 'E', 'F'],
                [1, con('v1H'), con('v2H'), con('v3H'), con('v4H'), con('v5H')],
                [4, con('v11'), ex('value5'), con('v31'), con('v41'), con('v51')],
                [5, con('v12'), ex('value1'), con('v32'), ex('value2'), con('v52')],
                [6, con('v13'), ex('value6'), con('v33'), con('v43'), con('v53')],
                [7, con('v14'), ex('value3'), con('v34'), ex('value4'), con('v54')],
                [8, con('v15'), ex('value7'), con('v35'), con('v45'), con('v55')],
            ]
        }

    @pytest.mark.parametrize('openpyxl_workbook', [None, {'Sheet 1': {}}])
    def test_required_single(self, openpyxl_workbook):
        '''
        An example of a `required` validation error is missing the
        `col_alpha` and `value` keys. (There is no cell to reference,
        because it is missing.)

        '''
        assert spreadsheet_style_errors_table([
            {
                'sheet': 'Sheet 1',
                'row_number': 5,
            }
        ], openpyxl_workbook) == {
            'Sheet 1': [
                ['', '???'],
                [5, ex('')],
            ]
        }

    @pytest.mark.parametrize('openpyxl_workbook', [None, {'Sheet 1': {}}])
    def test_array_too_short_single(self, openpyxl_workbook):
        '''
        Validation error that array is too short has no spreadsheet information.
        '''
        assert spreadsheet_style_errors_table([
            {
            }
        ], openpyxl_workbook) == {
            None: [
                ['', '???']
            ]
        }
