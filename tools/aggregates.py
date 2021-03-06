#!/usr/bin/env python3
import json
from lib360dataquality.cove.threesixtygiving import get_grants_aggregates


def replace_none_keys(nested_data):
    """
    Walk a dict or list and replace any `None` keys with `'None'`.

    Replacement is done in place.

    """
    if hasattr(nested_data, "items"):
        for key, value in nested_data.items():
            if key is None:
                nested_data[str(key)] = value
            replace_none_keys(value)
    elif isinstance(nested_data, str):
        return
    elif hasattr(nested_data, "__iter__"):
        for item in nested_data:
            replace_none_keys(item)


data_all = json.load(open("data/data_all.json"))
stats = []

for dataset in data_all:
    json_filename = "data/json_all/%s.json" % dataset["identifier"]

    # Check that we had a location where json_filename file downloaded to
    if dataset["datagetter_metadata"].get("json") and dataset["datagetter_metadata"]["valid"]:
        with open(json_filename) as fp:
            aggregates = get_grants_aggregates(json.load(fp))
        # replace sets with counts
        for k, v in list(aggregates.items()):
            if isinstance(v, set):
                aggregates[k + "_count"] = len(v)
                if k == "distinct_funding_org_identifier":
                    aggregates[k] = sorted(list(aggregates[k]))
                else:
                    del aggregates[k]
        aggregates = {
            k: sorted(list(v)) if isinstance(v, set) else v
            for k, v in aggregates.items()
        }
        dataset["datagetter_aggregates"] = aggregates
    replace_none_keys(dataset)
    stats.append(dataset)
    with open("data/status.json", "w") as fp:
        json.dump(stats, fp, indent="  ", sort_keys=True)
