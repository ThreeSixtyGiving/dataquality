from cove_project.settings import *  # noqa F401, F403
from lib360dataquality.cove.settings import COVE_CONFIG as COVE_CONFIG_PROD


DATA_SUBMISSION_ENABLED = True

COVE_TEST = COVE_CONFIG_PROD

# Many of the test current utilise direct ?source_url= parameter calls which are
# now disabled by default, to use them a CSRF token has to be validated however
# these tests aren't using django's test runner so the options for fixing this
# are quite limited.

COVE_TEST["allow_direct_web_fetch"] = True

COVE = COVE_TEST
