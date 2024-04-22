from setuptools import setup, find_packages
from typing import List

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Declaring variables for setup functions
PROJECT_NAME = "src"
VERSION = "0.0.1"
AUTHOR = "Hasanain"
USER_NAME = "hasanain"
AUTHOR_EMAIL = "hasanain@cplusoft.com"
REPO_NAME = "callback-jack"
DESRCIPTION = "Can carry on a conversation on what is entered into the data base as to the best answer. This AI would be be for mainly taking customer service calls as well as booking appointments via warm leads and cold leads."
REQUIREMENT_FILE_NAME = "requirements.txt"
LICENSE = "MIT"
PYTHON_REQUIRES = ">=3.10"

HYPHEN_E_DOT = "-e ."


def get_requirements_list() -> List[str]:
    """
    Description: This function is going to return list of requirement
    mention in requirements.txt file
    return This function is going to return a list which contain name
    of libraries mentioned in requirements.txt file
    """
    with open(REQUIREMENT_FILE_NAME) as requirement_file:
        requirement_list = requirement_file.readlines()
        requirement_list = [
            requirement_name.replace("\n", "") for requirement_name in requirement_list
        ]
        if HYPHEN_E_DOT in requirement_list:
            requirement_list.remove(HYPHEN_E_DOT)
        return requirement_list


setup(
    name=PROJECT_NAME,
    version=VERSION,
    author=AUTHOR,
    description=DESRCIPTION,
    long_description=long_description,
    url=f"https://github.com/{USER_NAME}/{REPO_NAME}",
    packages=find_packages(),
    license=LICENSE,
    python_requires=PYTHON_REQUIRES,
    install_requires=get_requirements_list(),
)
