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
    classifiers=[
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3.6',
    ],
)
