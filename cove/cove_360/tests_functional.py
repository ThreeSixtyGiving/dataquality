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
    if BROWSER == 'ChromeHeadless':
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        # uncomment this if "DevToolsActivePort" error
        # chrome_options.add_argument("--remote-debugging-port=9222")
        browser = webdriver.Chrome(chrome_options=chrome_options)
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
    ('fundingproviders-grants_fixed_2_grants.json', ['A file was downloaded from',
                                                  'There are 4 grants to 2 recipient organisations and 0 to recipient individuals',
                                                  'The grants were awarded in GBP with a total value of £662,990 and individual awards ranging from £152,505 (lowest) to £178,990 (highest)',
                                                  'Convert to Spreadsheet',
                                                  'data does not use the 360Giving Data Standard correctly 15 Errors',
                                                  'your data is not yet using the 360Giving Data Standard',
                                                  'Incorrect Formats',
                                                  'Non-unique id values',
                                                  '4 grants do not contain any beneficiary location fields',
                                                  'Unique grant identifiers:  2',
                                                  'Unique funder organisation identifiers:  1',
                                                  '360G-fundingproviders-000002/X/00/X'], True),
    ('fundingproviders-grants_broken_grants.json', ['data does not use the 360Giving Data Standard correctly 15 Errors',
                                                 'Check your data 4 Grants',
                                                 'Unique funder organisation identifiers:  2',
                                                 'Unique recipient organisation identifiers:  2',
                                                 '360G-fundingproviders-000002/X/00/X'], True),
    ('fundingproviders-grants_2_grants.xlsx', ['Data about 1 funder',
                                            'There are 2 grants to 1 recipient organisation and 0 to recipient individuals',
                                            'The grants were awarded in GBP with a total value of £331,495',
                                            # check that there's no errors after the heading
                                            'Data conversion successful\nBefore checking',
                                            'data does not use the 360Giving Data Standard correctly 7 Errors',
                                            'description is missing but required',
                                            'Sheet: grants Row: 2',
                                            'Check your data 2 Grants',
                                            'Unique funder organisation identifiers:  1',
                                            'Unique recipient organisation identifiers:  1',
                                            '360G-fundingproviders-000002/X/00/X'], True),
    # Test conversion warnings are shown
    ('tenders_releases_2_releases.xlsx', ['Data conversion unsuccessful - 5 Errors have been found',
                                          'data does not use the 360Giving Data Standard correctly 76 Errors',
                                          'You may have a duplicate Identifier: We couldn\'t merge these rows with the id "1": field "ocid" in sheet "items": one cell has the value: "PW-14-00627094", the other cell has the value: "PW-14-00629344"'
                                          ], True),
    # Test that titles that aren't in the rollup are converted correctly
    # (See @check_url_input_result_page).
    ('fundingproviders-grants_2_grants_titleswithoutrollup.xlsx', [], True),
    # Test a 360 csv in cp1252 encoding
    ('fundingproviders-grants_2_grants_cp1252.csv', ['Data about 1 funder',
                                                  'There are 2 grants to 1 recipient organisation and 0 to recipient individuals',
                                                  'The grants were awarded in GBP with a total value of £331,495',
                                                  'This file is not \'utf-8\' encoded (it is cp1252 encoded)'], True),
    # Test a non-valid file.
    ('fundingtrust-grants_dc.txt', 'We can only process json, csv, ods and xlsx files', False),
    # Test a unconvertable spreadsheet (blank file)
    ('bad.xlsx', 'We think you tried to supply a spreadsheet, but we failed to convert it.', False),
    # Check that a file with a UTF-8 BOM converts correctly
    ('bom.csv', 'Unique grant identifiers:  1', True),
    ('nulls.json', [
        'is not a JSON array',
        'Date is not in the correct format',
        'Invalid code found in countryCode',
        'is not a number',
        'is not a string',
    ], True),
    ('decimal_amounts.csv', 'The grants were awarded in GBP with a total value of £7,000.7 and individual awards ranging from £1,000.1 (lowest) to £1,000.1 (highest).', True),
    ('decimal_amounts.json', 'The grants were awarded in GBP with a total value of £7,000.7 and individual awards ranging from £1,000.1 (lowest) to £1,000.1 (highest).', True),
    ('validation_errors-3.json', 'Something went wrong', False),
    ('badfile_all_validation_errors.json', [
        'description is missing but required (more info about this error)',
        'id is missing but required within recipientOrganization (more info about this error)',
        'Date is not in the correct format (more info about this error)',
        '0 is not a JSON object',
        'amountAwarded is not a number. Check that the value is not null, and doesn’t contain any characters other than 0-9 and dot (.). Number values should not be in quotes.',
        'plannedDates is not a JSON array',
        'title is not a string. Check that the value is not null, and has quotes at the start and end. Escape any quotes in the value with \ (more info about this error)',
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
    if 'CUSTOM_SERVER_URL' in os.environ:
        # Use urls pointing to GitHub if we have a custom (probably non local) server URL
        source_url = 'https://raw.githubusercontent.com/ThreeSixtyGiving/dataquality/main/cove/cove_360/fixtures/' + source_filename
        if authed:
            pytest.skip()
    else:
        source_url = httpserver.url + PREFIX_360 + source_filename

    if authed:
        User = get_user_model()
        user = User.objects.create_user(username='myuser', password='password')
        force_login(user, browser, server_url)

    browser.get(server_url)
    browser.find_element_by_class_name("cookie-consent-no").click()
    browser.find_element_by_partial_link_text('Link').click()
    time.sleep(0.5)
    browser.find_element_by_id('id_source_url').send_keys(source_url)
    browser.find_element_by_css_selector("#fetchURL > div.form-group > button.btn.btn-primary").click()

    # Wait for the various redirects after click
    wait_for_results_page(browser)

    data_url = browser.current_url

    # Click and un-collapse all explore sections
    all_sections = browser.find_elements_by_class_name('panel-heading')
    browser.find_element_by_class_name("cookie-consent-no").click()
    for section in all_sections:
        if section.get_attribute('data-toggle') == "collapse" and section.get_attribute('aria-expanded') != 'true':
            section.click()
        time.sleep(0.5)

    # Do the assertions
    check_url_input_result_page(server_url, browser, httpserver, source_filename, expected_text, conversion_successful, authed)

    if conversion_successful:
        # Expand all sections with the expand all button this time
        browser.find_element_by_link_text('Expand all').click()

        browser.get(data_url + '/advanced')
        assert 'Advanced view' in browser.find_element_by_tag_name('body').text


def check_url_input_result_page(server_url, browser, httpserver, source_filename, expected_text, conversion_successful, authed):
    body_text = browser.find_element_by_tag_name('body').text
    body_text += browser.page_source

    if isinstance(expected_text, str):
        expected_text = [expected_text]

    for text in expected_text:
        assert text in body_text

    if source_filename == 'validation_errors-3.json':
        assert 'UNSAFE' not in body_text

    assert 'Data Quality Tool' in browser.find_element_by_class_name('title360').text
    assert '360Giving' in browser.find_element_by_tag_name('body').text

    if conversion_successful:
        if source_filename.endswith('.json'):
            if authed:
                assert 'Original file (json)' in body_text
                original_file = browser.find_element_by_link_text('Original file (json)').get_attribute("href")
            else:
                assert 'Original file (json)' not in body_text
        elif source_filename.endswith('.xlsx'):
            if authed:
                assert 'Original file (xlsx)' in body_text
                original_file = browser.find_element_by_link_text('Original file (xlsx)').get_attribute("href")
            else:
                assert 'Original file (xlsx)' not in body_text
            assert 'JSON (Converted from Original) ' in body_text
            converted_file = browser.find_element_by_link_text("JSON (Converted from Original)").get_attribute("href")
            assert "unflattened.json" in converted_file
        elif source_filename.endswith('.csv'):
            if authed:
                assert 'Original file (csv)' in body_text
                original_file = browser.find_element_by_link_text('Original file (csv)').get_attribute("href")
            else:
                assert 'Original file (csv)' not in body_text
            converted_file = browser.find_element_by_link_text("JSON (Converted from Original)").get_attribute("href")
            assert "unflattened.json" in browser.find_element_by_link_text("JSON (Converted from Original)").get_attribute("href")

        # Test for Load New File button
        assert 'Load New File' in body_text

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
    # If we're testing a remove server then we can't run this test as we can't
    # set up the mocks
    if 'CUSTOM_SERVER_URL' in os.environ:
        pytest.skip()
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
    browser.get(server_url + '?source_url=' + source_url)

    if source_filename.endswith('.json'):
        browser.find_element_by_name("flatten").click()

    time.sleep(3)

    assert 'Warning' not in browser.find_element_by_tag_name("body").text

    warning_heading = "Data conversion unsuccessful - 1 Error has been found"

    conversion_title = browser.find_element_by_id('conversion-title')
    conversion_title_text = conversion_title.text

    if iserror:
        if flatten_or_unflatten == 'flatten':
            assert warning_heading in conversion_title_text
        else:
            assert warning_heading in conversion_title_text
        # should be a cross
        assert conversion_title.find_element_by_class_name('font-tick').get_attribute('class') == 'font-tick cross'
        browser.find_element_by_class_name("cookie-consent-no").click()
        conversion_title.click()
        time.sleep(2)
        assert warning_args[0] in browser.find_element_by_id('conversion-body').text
    else:
        if flatten_or_unflatten == 'flatten':
            assert warning_heading not in conversion_title_text
        else:
            assert warning_heading not in conversion_title_text
        # should be a tick
        assert conversion_title.find_element_by_class_name('font-tick').get_attribute('class') == 'font-tick tick'


@pytest.mark.parametrize(('link_text', 'url'), [
    ('360Giving', 'https://www.threesixtygiving.org/'),
    ('Publisher Guidance', 'https://standard.threesixtygiving.org/en/latest/'),
    ('Common Errors', 'common_errors'),
    ])
def test_footer_360(server_url, browser, link_text, url):
    browser.get(server_url)
    link = browser.find_element_by_link_text(link_text)
    href = link.get_attribute("href")
    assert url in href


def test_index_page_360(server_url, browser):
    browser.get(server_url)
    assert 'Data Quality Tool' in browser.find_element_by_class_name('title360').text
    assert 'How to check your data' in browser.find_element_by_tag_name('body').text
    assert 'Summary Spreadsheet - ' in browser.find_element_by_tag_name('body').text
    assert 'JSON built to the 360Giving JSON schema' in browser.find_element_by_tag_name('body').text
    assert 'Multi-table data package - Excel' in browser.find_element_by_tag_name('body').text
    assert '360Giving' in browser.find_element_by_tag_name('body').text


@pytest.mark.parametrize(('link_text', 'url'), [
    ('360Giving Data Standard guidance', 'https://standard.threesixtygiving.org/en/latest/technical/reference/#reference'),
    ('Excel', 'https://threesixtygiving-standard.readthedocs.io/en/latest/_static/summary-table/360-giving-schema-titles.xlsx'),
    ('CSV', 'https://standard.threesixtygiving.org/en/latest/technical/templates-csv/'),
    ('360Giving JSON schema', 'https://standard.threesixtygiving.org/en/latest/reference/#giving-json-schemas'),
    ('Multi-table data package - Excel', 'https://threesixtygiving-standard.readthedocs.io/en/latest/_static/multi-table/360-giving-schema-fields.xlsx')
    ])
def test_index_page_360_links(server_url, browser, link_text, url):
    browser.get(server_url)
    link = browser.find_element_by_link_text(link_text)
    href = link.get_attribute("href")
    assert url in href


def test_common_index_elements(server_url, browser):
    browser.get(server_url)
    browser.find_element_by_css_selector('#more-information .panel-title').click()
    time.sleep(0.5)
    assert 'What happens to the data I provide to this site?' in browser.find_element_by_tag_name('body').text
    assert 'Why do you delete data after seven days?' in browser.find_element_by_tag_name('body').text
    assert 'Why provide converted versions?' in browser.find_element_by_tag_name('body').text
    assert 'Terms & Conditions' in browser.find_element_by_tag_name('body').text
    assert '360Giving' in browser.find_element_by_tag_name('body').text


def test_terms_page(server_url, browser):
    browser.get(server_url + 'terms/')
    assert 'Open Data Services Co-operative Limited' in browser.find_element_by_tag_name('body').text
    assert 'Open Data Services Limited' not in browser.find_element_by_tag_name('body').text
    assert '360Giving' in browser.find_element_by_tag_name('body').text


def test_accordion(server_url, browser):
    browser.get(server_url)

    def buttons():
        return [b.is_displayed() for b in browser.find_elements(By.CSS_SELECTOR, "#accordion button")]

    time.sleep(0.5)
    assert buttons() == [True, False, False]
    assert 'Upload a file' in browser.find_elements_by_tag_name('label')[0].text
    browser.find_element_by_class_name("cookie-consent-no").click()
    browser.find_element_by_partial_link_text('Link').click()
    browser.implicitly_wait(1)
    time.sleep(0.5)
    assert buttons() == [False, True, False]
    browser.find_element_by_partial_link_text('Paste').click()
    time.sleep(0.5)
    assert buttons() == [False, False, True]
    assert 'Paste (JSON only)' in browser.find_elements_by_tag_name('label')[2].text

    # Now test that the whole banner is clickable
    browser.find_element_by_id('headingOne').click()
    time.sleep(0.5)
    assert buttons() == [True, False, False]
    browser.find_element_by_id('headingTwo').click()
    time.sleep(0.5)
    assert buttons() == [False, True, False]
    browser.find_element_by_id('headingThree').click()
    time.sleep(0.5)
    assert buttons() == [False, False, True]


@pytest.mark.parametrize(('source_filename'), [
    ('fundingproviders-grants_fixed_2_grants.json'),
    ])
def test_error_modal(server_url, browser, httpserver, source_filename):
    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())
    if 'CUSTOM_SERVER_URL' in os.environ:
        # Use urls pointing to GitHub if we have a custom (probably non local) server URL
        source_url = 'https://raw.githubusercontent.com/ThreeSixtyGiving/dataquality/main/cove/cove_360/fixtures/' + source_filename
    else:
        source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)
    browser.find_element_by_class_name("cookie-consent-no").click()
    browser.find_element_by_partial_link_text('Link').click()
    time.sleep(0.5)
    browser.find_element_by_id('id_source_url').send_keys(source_url)
    browser.find_element_by_css_selector("#fetchURL > div.form-group > button.btn.btn-primary").click()

    time.sleep(1)

    # Click and un-collapse all explore sections
    all_sections = browser.find_elements_by_class_name('panel-heading')
    browser.find_element_by_class_name("cookie-consent-no").click()
    for section in all_sections:
        if section.get_attribute('data-toggle') == "collapse" and section.get_attribute('aria-expanded') != 'true':
            section.click()
        time.sleep(0.5)

    table_rows = browser.find_elements_by_css_selector('.validation-errors-format-1 tbody tr')
    assert len(table_rows) == 4

    browser.find_element_by_css_selector('a[data-target=".validation-errors-format-2"]').click()

    modal = browser.find_element_by_css_selector('.validation-errors-format-2')
    assert "in" in modal.get_attribute("class").split()
    modal_text = modal.text
    assert "24/07/2014" in modal_text
    assert "grants/0/awardDate" in modal_text

    browser.find_element_by_css_selector('div.modal.validation-errors-format-2 button.close').click()
    browser.find_element_by_css_selector('a[data-target=".usefulness-checks-2"]').click()

    modal_additional_checks = browser.find_element_by_css_selector('.usefulness-checks-2')
    assert "in" in modal_additional_checks.get_attribute("class").split()
    modal_additional_checks_text = modal_additional_checks.text
    assert "4 recipient organisation grants do not have recipient organisation location information" in modal_additional_checks_text
    assert "grants/0/recipientOrganization/0/id" in modal_additional_checks_text
    table_rows = browser.find_elements_by_css_selector('.usefulness-checks-2 tbody tr')
    assert len(table_rows) == 4


@pytest.mark.parametrize(('source_filename', 'expected_text'), [
    ('fundingproviders-grants_fixed_2_grants.json', '360Giving JSON Package Schema')
    ])
def test_check_schema_link_on_result_page(server_url, browser, httpserver, source_filename, expected_text):
    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())
    if 'CUSTOM_SERVER_URL' in os.environ:
        # Use urls pointing to GitHub if we have a custom (probably non local) server URL
        source_url = 'https://raw.githubusercontent.com/ThreeSixtyGiving/dataquality/main/cove/cove_360/fixtures/' + source_filename
    else:
        source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)
    browser.find_element_by_class_name("cookie-consent-no").click()
    browser.find_element_by_partial_link_text('Link').click()
    time.sleep(0.5)
    browser.find_element_by_id('id_source_url').send_keys(source_url)
    browser.find_element_by_css_selector("#fetchURL > div.form-group > button.btn.btn-primary").click()

    time.sleep(1)

    # Click and un-collapse all explore sections
    all_sections = browser.find_elements_by_class_name('panel-heading')
    browser.find_element_by_class_name("cookie-consent-no").click()
    for section in all_sections:
        if section.get_attribute('data-toggle') == "collapse" and section.get_attribute('aria-expanded') != 'true':
            section.click()
        time.sleep(0.5)
    schema_link = browser.find_element_by_link_text(expected_text)
    schema_link.click()
    browser.find_element_by_id('giving-json-schemas')


@pytest.mark.parametrize(('data_url'), [
    reverse_lazy('results', args=['0']),
    reverse_lazy('results', args=['324ea8eb-f080-43ce-a8c1-9f47b28162f3']),
])
def test_url_invalid_dataset_request(server_url, browser, data_url):
    # Test a badly formed hexadecimal UUID string
    # Trim the / off reverse_lazy result as server_url has trailing slash to avoid
    # e.g. //results/0
    browser.get("%s%s" % (server_url, data_url[1:]))
    assert "We don't seem to be able to find the data you requested." in browser.find_element_by_tag_name('body').text
    # Test for well formed UUID that doesn't identify any dataset that exists
    browser.get("%s%s" % (server_url, reverse_lazy('results', args=['38e267ce-d395-46ba-acbf-2540cdd0c810'])[1:]))
    assert "We don't seem to be able to find the data you requested." in browser.find_element_by_tag_name('body').text
    assert '360Giving' in browser.find_element_by_tag_name('body').text
    #363 - Tests there is padding round the 'go to home' button
    success_button = browser.find_element_by_class_name('success-button')
    assert success_button.value_of_css_property('padding-bottom') == '20px'


def test_500_error(server_url, browser):
    browser.get(server_url + 'test/500')
    # Check that our nice error message is there
    assert 'Something went wrong' in browser.find_element_by_tag_name('body').text
    # Check for the exclamation icon
    # This helps to check that the theme including the css has been loaded
    # properly
    icon_span = browser.find_element_by_class_name('panel-danger').find_element_by_tag_name('span')
    assert 'Glyphicons Halflings' in icon_span.value_of_css_property('font-family')
    assert icon_span.value_of_css_property('color') == 'rgba(255, 255, 255, 1)'


def test_common_errors_page(server_url, browser):
    browser.get(server_url + 'common_errors/')
    assert "Common Errors" in browser.find_element_by_tag_name('h2').text
    assert '360Giving' in browser.find_element_by_tag_name('h1').text


@pytest.mark.parametrize(('anchor_text'), [
    ('uri'),
    ('date-time'),
    ('required'),
    ('enum'),
    ('string'),
    ('number')
    ])
def test_common_errors_page_anchors(server_url, browser, anchor_text):
    # Checks we have sections for each our error messages
    browser.get(server_url + 'common_errors/')
    browser.find_element_by_id(anchor_text)


def test_favicon(server_url, browser):
    browser.get(server_url)
    # we should not have a favicon link just now
    with pytest.raises(NoSuchElementException):
        browser.find_element_by_xpath("//link[@rel='icon']")


def test_explore_360_sample_data_link(server_url, browser):
    browser.get(server_url)
    browser.find_element_by_partial_link_text('loading some sample data.').click()

    wait_for_results_page(browser)

    body_text = browser.find_element_by_tag_name('body').text

    assert 'Summary: Your data at a glance' in body_text
    assert 'Sorry, we can\'t process that data' not in body_text
    # Show sample data link in the home page only
    with pytest.raises(NoSuchElementException):
        browser.find_element_by_partial_link_text('loading some sample data.')


def test_publishing_invalid_domain(server_url, browser):
    settings.DATA_SUBMISSION_ENABLED = True
    os.environ["REGISTRY_PUBLISHERS_URL"] = "https://raw.githubusercontent.com/ThreeSixtyGiving/dataquality/main/cove/cove_360/fixtures/publishers.json"

    browser.get(server_url)

    # Dismiss the cookie popup
    browser.find_element_by_class_name("cookie-consent-no").click()

    url_input = browser.find_element(By.CSS_SELECTOR, "#self-publishing-form input[type='url']")
    url_input.send_keys("https://raw.githubusercontent.com/OpenDataServices/grantnav-sampledata/master/grantnav-20180903134856.json")

    browser.find_element(By.ID, "submit-for-publishing-btn").click()

    # Wait for the processing redirect
    wait_for_results_page(browser)

    assert "(raw.githubusercontent.com) is not authorised for publishing 360Giving data." in browser.find_element(By.ID, "publisher-not-found-message").text


def test_codelist_validation(server_url, browser, httpserver):
    source_filename = 'codelist.csv'

    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())
    if 'CUSTOM_SERVER_URL' in os.environ:
        # Use urls pointing to GitHub if we have a custom (probably non local) server URL
        source_url = 'https://raw.githubusercontent.com/ThreeSixtyGiving/dataquality/main/cove/cove_360/fixtures/' + source_filename
    else:
        source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)
    browser.find_element_by_class_name("cookie-consent-no").click()
    browser.find_element_by_partial_link_text('Link').click()
    time.sleep(0.5)
    browser.find_element_by_id('id_source_url').send_keys(source_url)
    browser.find_element_by_css_selector("#fetchURL > div.form-group > button.btn.btn-primary").click()

    time.sleep(1)

    browser.find_element_by_class_name("cookie-consent-no").click()
    time.sleep(0.5)

    # Click and un-collapse validation section
    browser.find_element_by_id('validation-panel-heading').click()
    time.sleep(0.5)

    validation_body_text = browser.find_element_by_id('validation-body').text
    assert "Codelist Errors" in validation_body_text
    assert "BAD" in validation_body_text
    assert "FRG010" not in validation_body_text


def test_oneof_validation(server_url, browser, httpserver):
    source_filename = 'oneof.csv'

    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())
    if 'CUSTOM_SERVER_URL' in os.environ:
        # Use urls pointing to GitHub if we have a custom (probably non local) server URL
        source_url = 'https://raw.githubusercontent.com/ThreeSixtyGiving/dataquality/main/cove/cove_360/fixtures/' + source_filename
    else:
        source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)
    browser.find_element_by_class_name("cookie-consent-no").click()
    browser.find_element_by_partial_link_text('Link').click()
    time.sleep(0.5)
    browser.find_element_by_id('id_source_url').send_keys(source_url)
    browser.find_element_by_css_selector("#fetchURL > div.form-group > button.btn.btn-primary").click()

    time.sleep(1)

    browser.find_element_by_class_name("cookie-consent-no").click()
    time.sleep(0.5)

    # Click and un-collapse validation section
    browser.find_element_by_id('validation-panel-heading').click()
    time.sleep(0.5)

    validation_body_text = browser.find_element_by_id('validation-body').text
    assert "Only 1 of recipientOrganization or recipientIndividual is permitted, but both are present" in validation_body_text
    validation_body_html = browser.find_element_by_id("validation-body").get_attribute("innerHTML")
    assert "Only 1 of <code>recipientOrganization</code> or <code>recipientIndividual</code> is permitted, but both are present" in validation_body_html


@pytest.mark.parametrize(('source_filename', 'expected_texts', 'unexpected_texts'), [
    ("RecipientIndWithoutToIndividualsDetails.xlsx", [
        "1 recipient individual grant has Recipient Ind but no To Individuals Details:Grant Purpose or To Individuals Details:Primary Grant Reason",
        "Your data contains grants to individuals, but without the grant purpose or grant reason codes. This can make it difficult to use data on grants to individuals, as much of the information is anonymised, so it is recommended that you share these codes for all grants to individuals.",
        "Sheet: grants Row: 2 Header: Recipient Ind:Identifier",
    ], []),
    ("RecipientIndDEI.json", [
        "1 recipient individual grant has Recipient Ind and DEI information",
        "Your data contains grants to individuals which also have DEI (Diversity, Equity and Inclusion) information. You must not share any DEI data about individuals as this can make them personally identifiable when combined with other information in the grant.",
        "grants/0/recipientIndividual/id",
    ], []),
    # If there's a Postcode, but no Recipient Ind, there should be no message
    ("GeoCodePostcode.xlsx", [], [
        "looks like a postcode",
        "Sheet: grants Row: 3 Header: Beneficiary Location:Geographic Code",
        "Sheet: grants Row: 4 Header: Beneficiary Location:Geographic Code",
    ]),
    ("GeoCodePostcodeRecipientInd.xlsx", [
        "2 recipient individual grants have Geographic Code that looks like a postcode",
        "Your data contains a Beneficiary Location:Geographic Code that looks like a postcode on grants to individuals. You must not share any postcodes for grants to individuals as this can make them personally identifiable when combined with other information in the grant.",
        "Sheet: grants Row: 3 Header: Beneficiary Location:Geographic Code",
        "Sheet: grants Row: 4 Header: Beneficiary Location:Geographic Code",
    ], []),
])
def test_quality_checks(server_url, browser, httpserver, source_filename, expected_texts, unexpected_texts):
    with open(os.path.join('cove_360', 'fixtures', source_filename), 'rb') as fp:
        httpserver.serve_content(fp.read())
    if 'CUSTOM_SERVER_URL' in os.environ:
        # Use urls pointing to GitHub if we have a custom (probably non local) server URL
        source_url = 'https://raw.githubusercontent.com/ThreeSixtyGiving/dataquality/main/cove/cove_360/fixtures/' + source_filename
    else:
        source_url = httpserver.url + '/' + source_filename

    browser.get(server_url)
    browser.find_element_by_class_name("cookie-consent-no").click()
    browser.find_element_by_partial_link_text('Link').click()
    time.sleep(0.5)
    browser.find_element_by_id('id_source_url').send_keys(source_url)
    browser.find_element_by_css_selector("#fetchURL > div.form-group > button.btn.btn-primary").click()

    time.sleep(1)

    browser.find_element_by_class_name("cookie-consent-no").click()
    time.sleep(0.5)

    try:
        # Click and un-collapse quality accuracy section
        browser.find_element_by_id('quality-accuracy-panel-heading').click()
        time.sleep(0.5)

        quality_accuracy_body_text = browser.find_element_by_id('quality-accuracy-body').text
    except NoSuchElementException:
        quality_accuracy_body_text = ""

    for expected_text in expected_texts:
        assert expected_text in quality_accuracy_body_text, f"Expected: '{expected_text}'\nGot: '{quality_accuracy_body_text}'"
    for unexpected_text in unexpected_texts:
        assert unexpected_text not in quality_accuracy_body_text
