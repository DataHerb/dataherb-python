from setuptools import setup as _setup
from setuptools import find_packages as _find_packages
from dataherb.version import __version__

PACKAGE_NAME = 'dataherb'
PACKAGE_VERSION = __version__
PACKAGE_DESCRIPTION = 'Get clean datasets from DataHerb to boost your data science and data analysis projects'
PACKAGE_LONG_DESCRIPTION = (
      'DataHerb is a project to list curated datasets. '
      'The dataherb python package makes it easy to search, preview, and load data into your projects.'
      )
PACKAGE_URL = 'https://github.com/DataHerb/dataherb-python'

def _requirements():
    return [r for r in open('requirements.txt')]

def setup():
    _setup(
        name=PACKAGE_NAME,
        version=PACKAGE_VERSION,
        description=PACKAGE_DESCRIPTION,
        long_description=PACKAGE_LONG_DESCRIPTION,
        url=PACKAGE_URL,
        author='Lei Ma',
        author_email='hi@leima.is',
        license='MIT',
        packages=_find_packages(exclude=('tests',)),
        include_package_data=True,
        test_suite='nose.collector',
        tests_require=['nose'],
        zip_safe=False
    )

if __name__ == '__main__':
    setup()
    print("Packages: ", _find_packages(exclude=('tests',)))
