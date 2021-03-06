# Cove settings for 360

COVE_CONFIG = {
    'app_name': 'cove_360',
    'app_base_template': 'cove_360/base.html',
    'app_verbose_name': '360Giving Data Quality Tool',
    'app_strapline': 'Convert, Validate, Explore 360Giving Data',
    'schema_name': '360-giving-package-schema.json',
    'schema_item_name': '360-giving-schema.json',
    'schema_host': 'https://raw.githubusercontent.com/ThreeSixtyGiving/standard/master/schema/',
    'schema_version': None,
    'schema_version_choices': None,
    'root_list_path': 'grants',
    'root_id': '',
    'convert_titles': True,
    'input_methods': ['upload', 'url', 'text'],
    'support_email': 'support@threesixtygiving.org',
    'hashcomments': True
}
