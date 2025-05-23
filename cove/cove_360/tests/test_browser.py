from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.conf import settings
import pytest
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from seleniumlogin import force_login
import time
import os

import chromedriver_autoinstaller
import flattentool
import warnings
from flattentool.exceptions import DataErrorWarning
from selenium.webdriver.chrome.options import Options

BROWSER = os.environ.get('BROWSER', 'ChromeHeadless')

PREFIX_360 = os.environ.get('PREFIX_360', '/')

settings.DISABLE_COOKIE_POPUP = True

# Ensure the correct version of chromedriver is installed
try:
    chromedriver_autoinstaller.install()
except Exception as e:
    print(f"Chromedriver not auto installed: {e}")
    pass


def wait_for_results_page(browser):
    # Wait for the various redirects after click
    while "results" not in browser.current_url:
        time.sleep(0.5)


@pytest.fixture(scope="module")
def browser(request):
    if BROWSER == 'Chrome':
        chrome_options = Options()
        browser = webdriver.Chrome(options=chrome_options)
    elif BROWSER == 'ChromeHeadless':
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        # uncomment this if "DevToolsActivePort" error
        # chrome_options.add_argument("--remote-debugging-port=9222")
        browser = webdriver.Chrome(options=chrome_options)
    else:
        browser = getattr(webdriver, BROWSER)()

    browser.implicitly_wait(3)
    request.addfinalizer(lambda: browser.quit())
    return browser


@pytest.fixture(scope="module")
def server_url(request, live_server):
    if 'CUSTOM_SERVER_URL' in os.environ:
        return os.environ['CUSTOM_SERVER_URL'] + PREFIX_360
    else:
        return live_server.url + PREFIX_360


@pytest.mark.parametrize(('source_filename', 'expected_text', 'conversion_successful'), [
    ('fundingproviders-grants_fixed_2_grants.json', ["Total Grants\n4",
                                                     "Recipient Individuals\n0",
                                                  'GBP £662,990 £152,505 £178,990',  # Total amount, smallest , largest
                                                  'Convert to Spreadsheet',
                                                  'data does not use the 360Giving Data Standard correctly',
                                                  '15 Errors',
                                                  'your data is not yet using the 360Giving Data Standard',
                                                  'Incorrect Formats',
                                                  'Non-unique id values',
                                                  '4 grants do not contain any beneficiary location fields',
                                                  "Funding Organisations\n1",
                                                  '360G-fundingproviders-000002/X/00/X'], True),
    ('fundingproviders-grants_broken_grants.json', ['data does not use the 360Giving Data Standard correctly',
                                                    '15 Errors',
                                                 "Funding Organisations\n2",
                                                 "Recipient Organisations\n2",
                                                 '360G-fundingproviders-000002/X/00/X'], True),
    ('fundingproviders-grants_2_grants.xlsx', ["Funding Organisations\n1",
                                            "Total Grants\n2",
                                            "Recipient Organisations\n1",
                                            "Recipient Individuals\n0",
                                            'GBP £331,495',
                                            # check that there's no errors after the heading
                                            'data does not use the 360Giving Data Standard correctly',
                                            '7 Errors',
                                            'description is missing but required',
                                            "Funding Organisations\n1",
                                            "Recipient Organisations\n1"], True),
    # Test conversion warnings are shown
    ('tenders_releases_2_releases.xlsx', ['This data could not be converted (5 Errors)',
                                          'This data does not use the 360Giving Data Standard correctly (76 Errors )',

                                          'You may have a duplicate Identifier: We couldn\'t merge these rows with the id "1": field "ocid" in sheet "items": one cell has the value: "PW-14-00627094", the other cell has the value: "PW-14-00629344"'
                                          ], True),
    # Test that titles that aren't in the rollup are converted correctly
    # (See @check_url_input_result_page).
    ('fundingproviders-grants_2_grants_titleswithoutrollup.xlsx', [], True),
    # Test a 360 csv in cp1252 encoding
    ('fundingproviders-grants_2_grants_cp1252.csv', ["Funding Organisations\n1",
                                                     "Total Grants\n2",
                                                     "Recipient Organisations\n1",
                                                     "Recipient Individuals\n0",
                                                     'GBP £331,495',
                                                  'This file is not \'utf-8\' encoded (it is cp1252 encoded)'], True),
    # Test a non-valid file.
    ('fundingtrust-grants_dc.txt', 'We can only process json, csv, ods and xlsx files', False),
    # Test a unconvertable spreadsheet (blank file)
    ('bad.xlsx', 'We think you tried to supply a spreadsheet, but we failed to convert it.', False),
    # Check that a file with a UTF-8 BOM converts correctly
    ('bom.csv', "Total Grants\n1", True),
    ('nulls.json', [
        'is not a JSON array',
        'Date is not in the correct format',
        'is not a number',
        'is not a string',
    ], True),
    ('decimal_amounts.csv', 'GBP £7,000.7 £1,000.1 £1,000.1', True),  # £ Total, £min £max
    ('decimal_amounts.json', 'GBP £7,000.7 £1,000.1 £1,000.1', True),
    ('validation_errors-3.json', 'Something went wrong', False),
    ('badfile_all_validation_errors.json', [
        'description is missing but required (more info about this error)',
        'id is missing but required within recipientOrganization (more info about this error)',
        'Date is not in the correct format (more info about this error)',
        '0 is not a JSON object',
        'amountAwarded is not a number. Check that the value is not null, and doesn’t contain any characters other than 0-9 and dot (.). Number values should not be in quotes.',
        'plannedDates is not a JSON array',
        'title is not a string. Check that the value is not null, and has quotes at the start and end. Escape any quotes in the value with \\ (more info about this error)',
        'Invalid \'uri\' found (more info about this error)',
        'Invalid code found in currency (more info about this error)',
        '[] is too short. You must supply at least one value, or remove the item entirely (unless it’s required).',

    ], True),
    ('badfile_all_validation_errors.xlsx', [
        'description is missing but required (more info about this error)',
        'id is missing but required within recipientOrganization (more info about this error)',
        'Date is not in the correct format (more info about this error)',
        'Amount Awarded is not a number. Check that the value is not null, and doesn’t contain any characters other than 0-9 and dot (.). Number values should not be in quotes.',
        'Invalid \'uri\' found (more info about this error)',
        'Invalid code found in Currency (more info about this error)',
        '[] is too short. You must supply at least one value, or remove the item entirely (unless it’s required).',
        'bad date',
        'This should be a number',
        'This should be a uri',
        'bad currency',
    ], True),
    ('badfile_all_validation_errors_4_times.xlsx', [
        'Description is missing but required (more info about this error)',
        'id is missing but required within recipientOrganization (more info about this error)',
        'Date is not in the correct format (more info about this error)',
        'Amount Awarded is not a number. Check that the value is not null, and doesn’t contain any characters other than 0-9 and dot (.). Number values should not be in quotes.',
        'Invalid \'uri\' found (more info about this error)',
        'Invalid code found in Currency (more info about this error)',
        '[] is too short. You must supply at least one value, or remove the item entirely (unless it’s required).',
        # Context dates should be ISO formatted
        '2019-06-01T00:00:00+00:00',
        'bad date 1',
        'bad date 2',
        'bad date 3',
        'bad date 4',
        'This should be a number',
        'This should be a uri 1',
        'This should be a uri 2',
        # 'This should be a uri 3',
        'This should be a uri 5',
        'This should be a uri 6',
        # 'This should be a uri 7',
        'bad currency 1',
        'bad currency 2',
        'bad currency 3',
        'bad currency 4',
    ], True),
    ("dei_extension.xlsx", [
        "do not use the 360Giving Data Standard codelists correctly.",
    ], True),
    ("ids-unexpected-chars.xlsx", [
        "2 grants have a Funding or Recipient Organisation identifier that contains unexpected characters. If published this grant will not appear in GrantNav.",
        "1 grant has a Grant Identifier that contains unexpected characters. If published this grant will not appear in GrantNav."
    ], True),
    # TODO new tests here orgid-<>name
])
@pytest.mark.parametrize('authed', [True, False])
def test_explore_360_url_input(server_url, browser, httpserver, source_filename, expected_text, conversion_successful, authed):
    """
    TODO Test sequence: uploading JSON, files to Download only original, click convert,
    new http request, 'Data Summary' collapse. 'Download and Share' uncollapsed,
    converted files added.

    TODO Test file with grants in different currencies, check right text in 'Data Summary'

    TODO Test file with grants awarded on different dates, check right text in 'Data Summary'
    """

    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())

    source_url = httpserver.url + PREFIX_360 + source_filename

    if authed:
        User = get_user_model()
        user = User.objects.create_user(username='myuser', password='password')
        force_login(user, browser, server_url)

    browser.get(server_url)

    browser.find_element(By.ID, "link-tab-link").click()
    browser.find_element(By.ID, "id_source_url").send_keys(source_url)
    browser.find_element(By.ID, "submit-link-btn").click()

    # Wait for the various redirects after click
    wait_for_results_page(browser)

    # reload results page with ?open-all=true to see all values at once
    browser.get(f"{browser.current_url}?open-all=true")

    # Do the assertions
    check_url_input_result_page(server_url, browser, httpserver, source_filename, expected_text, conversion_successful, authed)


def check_url_input_result_page(server_url, browser, httpserver, source_filename, expected_text, conversion_successful, authed):
    body_text = browser.find_element(By.TAG_NAME, 'body').text
#    body_text += browser.page_source

    if isinstance(expected_text, str):
        expected_text = [expected_text]

    for text in expected_text:
        # print(f"looking for {text}")
        # print(f"in {body_text}")
        # input("continue?")
        assert text in body_text

    if source_filename == 'validation_errors-3.json':
        assert 'UNSAFE' not in body_text

    if conversion_successful:
        if source_filename.endswith('.json'):
            if authed:
                assert 'Original file (json)' in body_text
                original_file = browser.find_element(By.LINK_TEXT, 'Original file (json)').get_attribute("href")
            else:
                assert 'Original file (json)' not in body_text
        elif source_filename.endswith('.xlsx'):
            if authed:
                assert 'Original file (xlsx)' in body_text
                original_file = browser.find_element(By.LINK_TEXT, 'Original file (xlsx)').get_attribute("href")
            else:
                assert 'Original file (xlsx)' not in body_text
            assert 'JSON (Converted from Original) ' in body_text
            converted_file = browser.find_element(By.LINK_TEXT, "JSON (Converted from Original)").get_attribute("href")
            assert "unflattened.json" in converted_file
        elif source_filename.endswith('.csv'):
            if authed:
                assert 'Original file (csv)' in body_text
                original_file = browser.find_element(By.LINK_TEXT, 'Original file (csv)').get_attribute("href")
            else:
                assert 'Original file (csv)' not in body_text
            converted_file = browser.find_element(By.LINK_TEXT, "JSON (Converted from Original)").get_attribute("href")
            assert "unflattened.json" in browser.find_element(By.LINK_TEXT, "JSON (Converted from Original)").get_attribute("href")

        if authed:
            assert 'Note that this box and this download link are only visible to admin users' in body_text

            assert source_filename in original_file
            assert ' 0 bytes' not in body_text

            original_file_response = requests.get(original_file)
            assert original_file_response.status_code == 200
            assert int(original_file_response.headers['content-length']) != 0

        if source_filename.endswith('.xlsx') or source_filename.endswith('.csv'):
            converted_file_response = requests.get(converted_file)
            if source_filename == 'fundingproviders-grants_2_grants_titleswithoutrollup.xlsx':
                grant1 = converted_file_response.json()['grants'][1]
                assert grant1['recipientOrganization'][0]['department'] == 'Test data'
                assert grant1['classifications'][0]['title'] == 'Test'
            elif source_filename == 'bom.csv':
                assert converted_file_response.json()['grants'][0]['id'] == '42'
                assert 'This file is not \'utf-8\' encoded' not in body_text
            assert converted_file_response.status_code == 200
            assert int(converted_file_response.headers['content-length']) != 0


@pytest.mark.parametrize('iserror,warning_args', [
    (False, []),
    (True, ['Some warning', DataErrorWarning]),
    # Only warnings raised with the DataErrorWarning class should be shown
    # This avoids displaying messages like "Discarded range with reserved name"
    # https://github.com/OpenDataServices/cove/issues/444
    (False, ['Some warning'])
])
@pytest.mark.parametrize('flatten_or_unflatten', ['flatten', 'unflatten'])
def test_flattentool_warnings(server_url, browser, httpserver, monkeypatch, warning_args, flatten_or_unflatten, iserror):
    if flatten_or_unflatten == 'flatten':
        source_filename = 'example.json'
    else:
        source_filename = 'example.xlsx'

    def mockunflatten(input_name, output_name, *args, **kwargs):
        with open(kwargs['cell_source_map'], 'w') as fp:
            fp.write('{}')
        with open(kwargs['heading_source_map'], 'w') as fp:
            fp.write('{}')
        with open(output_name, 'w') as fp:
            fp.write('{}')
            if warning_args:
                warnings.warn(*warning_args)

    def mockflatten(input_name, output_name, *args, **kwargs):
        with open(output_name + '.xlsx', 'w') as fp:
            fp.write('{}')
            if warning_args:
                warnings.warn(*warning_args)

    mocks = {
        'flatten': mockflatten,
        'unflatten': mockunflatten
    }
    monkeypatch.setattr(flattentool, flatten_or_unflatten, mocks[flatten_or_unflatten])

    # Actual input doesn't matter, as we override
    # flattentool behaviour with a mock below
    httpserver.serve_content('{}')
    source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)

    browser.find_element(By.ID, "link-tab-link").click()
    browser.find_element(By.ID, "id_source_url").send_keys(source_url)
    browser.find_element(By.ID, "submit-link-btn").click()

    wait_for_results_page(browser)

    # The file conversion stuff is in the summary section of the results
    # (which is the default tab)

    if source_filename.endswith('.json'):
        browser.find_element(By.NAME, "flatten").click()

    time.sleep(2)

    assert 'Warning' not in browser.find_element(By.TAG_NAME, "body").text

    warning_heading = "Data conversion unsuccessful - 1 Error has been found"

    if iserror:
        conversion_title_text = browser.find_element(By.ID, "conversion-errors-area").text
        if flatten_or_unflatten == 'flatten':
            assert warning_heading in conversion_title_text
        else:
            # why does this repeat the above..
            assert warning_heading in conversion_title_text
        assert warning_args[0] in browser.find_element(By.ID, "conversion-errors-area").text
    else:
        if flatten_or_unflatten == 'flatten':
            success_title_text = browser.find_element(By.ID, "file-conversion-success-heading").text
            assert "File conversion successful" in success_title_text


@pytest.mark.parametrize(('source_filename'), [
    ('fundingproviders-grants_fixed_2_grants.json'),
    ])
def test_error_modal(server_url, browser, httpserver, source_filename):
    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())

    source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)

    browser.find_element(By.ID, "link-tab-link").click()
    browser.find_element(By.ID, "id_source_url").send_keys(source_url)
    browser.find_element(By.ID, "submit-link-btn").click()

    wait_for_results_page(browser)

    # reload results page with ?open-all=true to see all values at once
    browser.get(f"{browser.current_url}?open-all=true")

    table_rows = browser.find_elements(By.CSS_SELECTOR, ".validation-errors-format-1 tbody tr")
    assert len(table_rows) == 4

    browser.find_element(By.CSS_SELECTOR, "button[data-target-class=\"validation-errors-format-2\"]").click()

    modal = browser.find_element(By.CSS_SELECTOR, '.validation-errors-format-2')
    assert "modal--shown" in modal.get_attribute("class").split()
    modal_text = modal.text
    assert "24/07/2014" in modal_text
    assert "grants/0/awardDate" in modal_text

    browser.find_element(By.CSS_SELECTOR, ".validation-errors-format-2 .modal__close").click()

    browser.find_element(By.CSS_SELECTOR, "button[data-target-class=\"usefulness-checks-2\"]").click()

    modal_additional_checks = browser.find_element(By.CLASS_NAME, "usefulness-checks-2")
    assert "modal--shown" in modal_additional_checks.get_attribute("class").split()
    modal_additional_checks_text = modal_additional_checks.text
    assert "4 recipient organisation grants do not have recipient organisation location information" in modal_additional_checks_text
    assert "grants/0/recipientOrganization/0/id" in modal_additional_checks_text
    table_rows = browser.find_elements(By.CSS_SELECTOR, ".usefulness-checks-2 tbody tr")
    assert len(table_rows) == 4


def test_url_invalid_dataset_request(server_url, browser):
    # Test for well formed UUID that doesn't identify any dataset that exists
    browser.get("%s%s" % (server_url, reverse_lazy('results', args=['38e267ce-d395-46ba-acbf-2540cdd0c810'])))
    assert "We don't seem to be able to find the data you requested." in browser.find_element(By.TAG_NAME, 'body').text
    assert '360Giving' in browser.find_element(By.TAG_NAME, 'body').text


def test_500_error(server_url, browser):
    browser.get(server_url + 'test/500')
    # Check that our nice error message is there
    assert 'Something went wrong' in browser.find_element(By.TAG_NAME, 'body').text


def test_common_errors_page(server_url, browser):
    path = reverse_lazy("common_errors")
    browser.get(f"{server_url}/{path}")
    content = browser.find_element(By.CLASS_NAME, "layout__content").text
    # Make sure the expected page has loaded
    assert "Common Errors" in content
    # Make sure it is the 360Giving version
    assert "360Giving" in content


def test_favicon(server_url, browser):
    browser.get(server_url)
    # we should not have a favicon link just now
    with pytest.raises(NoSuchElementException):
        browser.find_element(By.XPATH, "//link[@rel='icon']")


def test_publishing_invalid_domain(server_url, browser):
    settings.DATA_SUBMISSION_ENABLED = True
    os.environ["REGISTRY_PUBLISHERS_URL"] = "https://raw.githubusercontent.com/ThreeSixtyGiving/dataquality/main/cove/cove_360/fixtures/publishers.json"

    path = reverse_lazy("publishing")
    browser.get(f"{server_url}/{path}")

    url_input = browser.find_element(By.ID, "source-url-input")
    url_input.send_keys("https://raw.githubusercontent.com/OpenDataServices/grantnav-sampledata/master/grantnav-20180903134856.json")

    browser.find_element(By.ID, "submit-for-publishing-btn").click()

    # Wait for the processing redirect
    wait_for_results_page(browser)

    assert "(raw.githubusercontent.com) is not authorised for publishing 360Giving data." in browser.find_element(By.ID, "publisher-not-found-message").text


def test_codelist_validation(server_url, browser, httpserver):
    source_filename = 'codelist.csv'

    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())

    source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)

    browser.find_element(By.ID, "link-tab-link").click()
    browser.find_element(By.ID, "id_source_url").send_keys(source_url)
    browser.find_element(By.ID, "submit-link-btn").click()

    wait_for_results_page(browser)
    # reload results page with ?open-all=true to see all values at once
    browser.get(f"{browser.current_url}?open-all=true")

    body_text = browser.find_element(By.TAG_NAME, "body").text

    assert "Codelist Errors" in body_text
    assert "BAD" in body_text
    assert "FRG010" not in body_text


def test_oneof_validation(server_url, browser, httpserver):
    source_filename = 'oneof.csv'

    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())

    source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)

    browser.find_element(By.ID, "link-tab-link").click()
    browser.find_element(By.ID, "id_source_url").send_keys(source_url)
    browser.find_element(By.ID, "submit-link-btn").click()

    wait_for_results_page(browser)
    # reload results page with ?open-all=true to see all values at once
    browser.get(f"{browser.current_url}?open-all=true")

    body_text = browser.find_element(By.TAG_NAME, "body").text

    assert "Only 1 of recipientOrganization or recipientIndividual is permitted, but both are present" in body_text


@pytest.mark.parametrize(('source_filename', 'expected_texts', 'unexpected_texts'), [
    ("RecipientIndWithoutToIndividualsDetails.xlsx", [
        "2 recipient individual grants have Recipient individual grant with no To Individuals Details:Grant Purpose or To Individuals Details:Primary Grant Reason",
        "Your data contains grants to individuals, but does not include grant purpose or grant reason codes. Including this information will make your data more useful and contribute to analysis of collective impact and trends over time."
    ], []),
    ("RecipientIndDEI.json", [
        "1 recipient individual grant has Recipient Ind and DEI information",
        "Your data contains grants to individuals which also have DEI (Diversity, Equity and Inclusion) information. You must not share any DEI data about individuals as this can make them personally identifiable when combined with other information in the grant.",
    ], []),
    # If there's a Postcode, but no Recipient Ind, there should be no message
    ("GeoCodePostcode.xlsx", [], [
        "looks like a postcode",
    ]),
    ("GeoCodePostcodeRecipientInd.xlsx", [
        "2 recipient individual grants have Geographic Code that looks like a postcode",
        "Your data contains a Beneficiary Location:Geographic Code that looks like a postcode on grants to individuals. You must not share any postcodes for grants to individuals as this can make them personally identifiable when combined with other information in the grant.",
    ], []),
    ("duration_usefulness.json", [
        "1 grant has neither a planned duration or start and end dates found",
        "Including both Planned Dates:Start Date and Planned Dates:End Date or Planned Dates:Duration (months) show the duration of the project or funding."
    ], []),
    ("additional_fields.json", [
        "Additional fields which do not use 360Giving Data Standard titles were found in your data.",
    ], []),
    ("multiple_funder_names_org_ids.json", [
        "introduced an additional Funding Org:Identifier for an existing Funding Org:Name"
    ], []),
])
def test_quality_checks(server_url, browser, httpserver, source_filename, expected_texts, unexpected_texts):
    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())

    source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)

    browser.find_element(By.ID, "link-tab-link").click()
    browser.find_element(By.ID, "id_source_url").send_keys(source_url)
    browser.find_element(By.ID, "submit-link-btn").click()

    wait_for_results_page(browser)

    # reload results page with ?open-all=true to see all values at once
    browser.get(f"{browser.current_url}?open-all=true")

    body_text = browser.find_element(By.TAG_NAME, 'body').text

    for expected_text in expected_texts:
        assert expected_text in body_text, f"Expected: '{expected_text}'\nGot: '{body_text}'"
    for unexpected_text in unexpected_texts:
        assert unexpected_text not in body_text


def test_file_submission(server_url, browser, httpserver):
    # This code doesn't work reliably on github actions. Leaving here for future refactoring efforts
    """
    Test the file submission process works to the point of getting to the "submit"
    into the sales force form

    This requires valid file submission settings via envs:

    "DATA_SUBMISSION_ENABLED"
    "REGISTRY_PUBLISHERS_URL"
    "REGISTRY_PUBLISHERS_USER"
    "REGISTRY_PUBLISHERS_PASS"

    Hint: Skip this test via pytest -k "not test_file_submission" if file
    submission credentials aren't available.
    """
    settings.DATA_SUBMISSION_ENABLED = True

    source_filename = "publishers.json"
    # Create a publishers registry entry
    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())

    os.environ["REGISTRY_PUBLISHERS_URL"] = f"{httpserver.url}/{source_filename}"

    path = reverse_lazy("publishing")
    browser.get(f"{server_url}/{path}")

    valid_for_publishing = "https://www.threesixtygiving.org/wp-content/uploads/love-kingston-funding-data-2018.xlsx"

    url_input = browser.find_element(By.ID, "source-url-input")
    url_input.send_keys(valid_for_publishing)

    browser.find_element(By.ID, "submit-for-publishing-btn").click()

    wait_for_results_page(browser)

    body_text = browser.find_element(By.TAG_NAME, "body").text

    assert "The data was checked and can now be submitted to the 360Giving Data Registry." in body_text, f"Expected '...can now be submitted' in {body_text}"


def test_cookie_popup(server_url, browser, httpserver):
    """ Test that re-enabling the cookie popup does what we expect by including the cookie template """
    settings.DISABLE_COOKIE_POPUP = False

    browser.get(server_url)

    assert "Allow analytics" in browser.find_element(By.ID, "cookie-dialog-title").text


@pytest.mark.parametrize(("location", "expected_texts"), [
    ("http://localhost:2134", "Sorry we got a ConnectionError whilst trying to download that file"),
    ("https://wrong.host.badssl.com", "misconfigured SSL certificates"),
    ("http://www.google.com/cove", "404 Client Error: Not Found for url"),
    ("http://example.org/", "Sorry, we can't process that data")
])
def test_input_http_errors(server_url, browser, httpserver, location, expected_texts):
    browser.get(server_url)

    browser.find_element(By.ID, "link-tab-link").click()
    browser.find_element(By.ID, "id_source_url").send_keys(location)
    browser.find_element(By.ID, "submit-link-btn").click()

    time.sleep(1)

    content_text = browser.find_element(By.CLASS_NAME, "layout__content").text

    assert expected_texts in content_text


def test_input_strange_files(server_url, browser, httpserver):
    def cove_url_input(url):
        browser.find_element(By.ID, "link-tab-link").click()
        browser.find_element(By.ID, "id_source_url").send_keys(url)
        browser.find_element(By.ID, "submit-link-btn").click()

    httpserver.serve_content('{}', headers={
        'content-type': 'text/csv'
    })

    browser.get(server_url)
    cove_url_input(httpserver.url)
    wait_for_results_page(browser)

    assert "file.csv" in browser.find_element(By.CSS_SELECTOR, ".layout__content h2").text

    httpserver.serve_content('{}', headers={
        'content-disposition': 'attachment; filename="something.csv"'
    })

    browser.get(server_url)
    cove_url_input(httpserver.url)
    wait_for_results_page(browser)

    assert "file.csv" in browser.find_element(By.CSS_SELECTOR, ".layout__content h2").text


def test_additional_checks_docs_page(server_url, browser, httpserver):
    path = reverse_lazy("additional_checks")
    browser.get(f"{server_url}{path}")

    assert "Class name: ZeroAmountTest" in browser.find_element(By.ID, "ZeroAmountTest").text
