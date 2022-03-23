# ThreeSixtyGiving Data Quality

This repository contains tools and libraries for checking and assessing the quality of data published to the ThreeSixtyGiving data standard.

## CoVE

[CoVE](https://github.com/OpenDataServices/cove) is a web application to Convert, Validate and Explore data that adheres to an open data standard. This repository contains a CoVE configured for the ThreeSixtyGiving data standard.

A live instance of CoVE is available at: [https://dataquality.threesixtygiving.org](https://dataquality.threesixtygiving.org)
### Installing and running for development

Install the python dependences:
```
$ virtualenv .ve --python python3
$ source .ve/bin/activate
$ pip install -r requirements_cove.txt
```

Start the development server:
```
$ ./cove/manage.py runserver
```

### Testing Cove

Install the python dependencies:
```
$ pip install -r requirements_cove_dev.txt
$ cd cove
$ py.test
```

### Deploying to production

CoVE is based on Django and be deployed using the deployment mechanisms as defined in the [Django docs](https://docs.djangoproject.com/en/3.1/howto/deployment/)


## lib360dataquality

lib360dataquality is a library that contains useful functions and classes for checking ThreeSixtyGiving standard data.

It is used by both tools and CoVE to generate reports on the data quality.

### Installing library

Install just the python library

```
$ virtualenv .ve --python python3
$ source .ve/bin/activate
$ pip install -e .
```

### Using the tools

The tools directory contains a number of command line tools that can be run on TheeSixtyGiving standard data to generate various reports.

Running various tools example:
```
cove_checks.py ../a001p00000tuoBKAAY.ods
```

### Using the python library

To use the python library import it into your python program, for example to use the additional checks:

```python
from lib360dataquality.cove.threesixtygiving import common_checks_360
from lib360dataquality.cove.schema import Schema360

context = { "file_type": "json" }
working_dir = os.path.abspath(os.path.curdir)

data = '' # Your JSON data

common_checks_360(context, working_dir, data, Schema360())

print(context)
```

## Code Linting

Code should pass `flake8`

New code should aim to pass python `black`