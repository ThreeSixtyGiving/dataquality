from setuptools import find_packages, setup

setup(
    name='lib360dataquality',
    version='0.0.1',
    author='Open Data Services',
    author_email='code@opendataservices.coop',
    url='https://github.com/threesixtygiving/dataquality',
    description='A data review library for the ThreeSixtyGiving data standard',
    license='AGPLv3',
    packages=find_packages(include=['lib360dataquality*']),
    long_description="A variety of library functions to asses the quality of data that is formatted in the ThreeSixtyGiving data standard",
    install_requires=[
        'libcove>=0.18.0',
        'python-dateutil',
        'rangedict',
        'ijson',
        'jsonschema<4',
        'json-merge-patch',
    ],
    extras_require={
        'perf': [
            'orjson>=3',
        ],
        'test': [
            'coveralls',
            'pytest',
            'pytest-cov',
            'isort',
        ],
    },
    scripts=[
        "tools/aggregates.py",
        "tools/check_grantnav_assumptions.py",
        "tools/cove_checks.py",
        "tools/coverage360.py",
        "tools/report.py",
        "tools/generate-reports.sh",
        "tools/deploy.sh",
    ],
    classifiers=[
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3.12',
    ],
)
