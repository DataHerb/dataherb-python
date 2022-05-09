from os import path

from setuptools import find_packages as _find_packages
from setuptools import setup as _setup

from dataherb.version import __version__

# read the contents of your README file
__CWD__ = path.abspath(path.dirname(__file__))
with open(path.join(__CWD__, "README.md"), encoding="utf-8") as fp:
    PACKAGE_LONG_DESCRIPTION = fp.read()


PACKAGE_NAME = "dataherb"
PACKAGE_VERSION = __version__
PACKAGE_DESCRIPTION = "Get clean datasets from DataHerb to boost your data science and data analysis projects"
PACKAGE_URL = "https://github.com/DataHerb/dataherb-python"


def _requirements():
    return [r for r in open("requirements.txt")]


def setup():
    _setup(
        name=PACKAGE_NAME,
        version=PACKAGE_VERSION,
        description=PACKAGE_DESCRIPTION,
        long_description=PACKAGE_LONG_DESCRIPTION,
        long_description_content_type="text/markdown",
        url=PACKAGE_URL,
        author="Lei Ma",
        author_email="hi@leima.is",
        license="MIT",
        packages=_find_packages(exclude=("tests",)),
        install_requires=_requirements(),
        include_package_data=True,
        entry_points={"console_scripts": ["dataherb=dataherb.command:dataherb"]},
        test_suite="nose.collector",
        tests_require=["nose"],
        zip_safe=False,
    )


if __name__ == "__main__":
    setup()
    print("Packages: ", _find_packages(exclude=("tests",)))
