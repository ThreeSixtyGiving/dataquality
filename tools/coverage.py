#!/usr/bin/env python3

import json
from lib360dataquality.cove.schema import Schema360
from lib360dataquality.coverage import get_unique_fields_present
from libcove.lib.common import get_fields_present


data_all = json.load(open('data/status.json'))
stats = []

schema_obj = Schema360()
schema_fields = schema_obj.get_pkg_schema_fields()


for dataset in data_all:
    json_filename = "data/json_all/%s.json" % dataset['identifier']
    # Check that we had a location where json_filename file downloaded to
    if dataset['datagetter_metadata'].get('json'):
        with open(json_filename) as fp:
            json_data = json.load(fp)
            fields_present = get_fields_present(json_data)
            unique_fields_present = get_unique_fields_present(json_data)
        dataset['datagetter_coverage'] = {}
        for field in fields_present:
            dataset['datagetter_coverage'][field] = {
                'total_fields': fields_present[field],
                'grants_with_field': unique_fields_present.get(field),
                'standard': field in schema_fields,
            }
    stats.append(dataset)
    with open('data/coverage.json', 'w') as fp:
        json.dump(stats, fp, indent='  ', sort_keys=True)
