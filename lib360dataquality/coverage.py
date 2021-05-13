import collections
from libcove.lib.common import fields_present_generator


def _unique_fields_present_generator(json_data):
    if not isinstance(json_data, dict):
        return
    if 'grants' not in json_data:
        return
    for grant in json_data['grants']:
        # Flatten the key,val pairs so we can make a unique list of fields
        field_list = [field for field, value in fields_present_generator(grant)]
        for field in set(field_list):
            yield '/grants' + field


def get_unique_fields_present(*args, **kwargs):
    counter = collections.Counter()
    counter.update(_unique_fields_present_generator(*args, **kwargs))
    return dict(counter)

