CoVE - Convert Validate & Explore
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Introduction
============

CoVE is an web application to Convert, Validate and Explore data following certain open data standards. http://cove.opendataservices.coop

Why convert data?
+++++++++++++++++

The W3C `Data on the Web Best Practices <http://www.w3.org/TR/dwbp/>`_ recommend making open data available in a range of formats to meet the needs of different users. Developers may want JSON, researchers might prefer a spreadsheet format.

CoVE manages the process of converting between JSON, Excel and CSV formats for structured data.

Validate and Explore
++++++++++++++++++++

CoVE presents key validation information during the process, and can be configured to display information about the contents of a data file, so that it can be easily inspected.

Supported formats
+++++++++++++++++

CoVE currently supports conversion from:

* JSON to multi-tabbed Excel files
* Excel to JSON (it uses the `flatten-tool <https://github.com/OpenDataServices/flatten-tool>`_ for conversion)

If a JSON schema is supplied, CoVE can use either field names or user-friendly column titles.

User Flows
==========

Overviews of how users flow through the application are maintained at https://docs.google.com/drawings/d/1pVbEu6dJaVk8t3NctjYuE5irsqltc9Th0gVQ_zeJyFA/edit and https://docs.google.com/drawings/d/1wFH4lZlBZWso7Tj_g7CyTF3YaFfnly59sVufpztmEg8/edit


Translations
============

| We use Django's translation framework to provide this application in different languages.
| We have used Google Translate to perform initial translations from English, but expect those translations to be worked on by humans over time.

Translations for Translators
++++++++++++++++++++++++++++
Translators can provide translations for this application by becoming a collaborator on Transifex https://www.transifex.com/OpenDataServices/cove

Translations for Developers
+++++++++++++++++++++++++++

For more information about Django's translation framework, see https://docs.djangoproject.com/en/1.8/topics/i18n/translation/

If you add new text to the interface, ensure to wrap it in the relevant gettext blocks/functions.

In order to generate messages and post them on Transifex:

First check the `Transifex lock <https://opendataservices.plan.io/projects/co-op/wiki/CoVE_Transifex_lock>`_, because only one branch can be translated on Transifex at a time.

Make sure you are set up as a maintainer in Transifex. Only maintainers are allowed to update the source file.

Install `gettext <https://www.gnu.org/software/gettext/>`_ library. (The following step is for Ubuntu but equivalent packages are available for other distros.)

.. code:: bash

    sudo apt-get install gettext

Then:

.. code:: bash

    python manage.py makemessages -l en
    tx push -s

In order to fetch messages from transifex:

.. code:: bash

    tx pull -a

In order to compile them:

.. code:: bash

    python manage.py compilemessages

Keep the makemessages and pull messages steps in thier own commits seperate from the text changes.

To check that all new text is written so that it is able to be translated you could install and run `django-template-i18n-lint`

.. code:: bash

    pip install django-template-i18n-lint
    django-template-i18n-lint cove