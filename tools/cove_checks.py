#!/usr/bin/env python3
import os
import argparse
import json
import pprint

from lib360dataquality.cove.threesixtygiving import common_checks_360
from lib360dataquality.cove.settings import COVE_CONFIG
from lib360dataquality.cove.schema import Schema360

from libcove.lib.converters import convert_spreadsheet
from libcove.config import LibCoveConfig


def main():
    parser = argparse.ArgumentParser(
        description="Check the data quality of some 360Giving standard data"
    )
    parser.add_argument("file_path", type=str, nargs=1, help="File for checking")
    parser.add_argument(
        "--type",
        dest="file_type",
        action="store",
        help="File type override",
        default=None,
    )

    args = parser.parse_args()

    working_dir = os.path.abspath(os.path.curdir)
    file_type = args.file_type
    # TODO Just dealing with one at a time
    file_path = args.file_path[0]
    schema = Schema360()

    if not file_type:
        file_type = os.path.splitext(file_path)[1][1:].lower()

    context = {"file_type": file_type}

    # We will need to convert it from a spreadsheet format first
    if file_type != "json":
        lib_cove_config = LibCoveConfig()
        lib_cove_config.config.update(COVE_CONFIG)
        context.update(
            convert_spreadsheet(
                working_dir,
                "null",
                file_path,
                file_type,
                lib_cove_config,
                schema.schema_url,
            )
        )
        with open(context["converted_path"], "r") as fp_data:
            data = json.load(fp_data)
    else:
        with open(file_path, "r") as fp_data:
            data = json.load(fp_data)

    common_checks_360(context, working_dir, data, schema)
    pprint.pprint(context)


if __name__ == "__main__":
    main()
