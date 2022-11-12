"""Python setup.py for HSM package"""
from setuptools import find_packages, setup

setup(
    name="HSM",
    version="0.0.0",
    description="PROJECT_DESCRIPTION",
    url="https://github.com/bswck/HSM/",
    long_description_content_type="text/markdown",
    author="bswck",
    packages=find_packages(exclude=["tests", ".github"]),
    entry_points={
        "console_scripts": ["HSM = HSM.__main__:main"]
    },
    extras_require={"test": ["pytest"]},
)
