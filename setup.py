import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ynapi-indexeng",
    version="0.0.7",
    author="Thomas Wallin",
    author_email="thomas.wallin89@gmail.com",
    description="YNAB API wrapper for python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/IndexEng/YNAPI",
    packages=['ynapi'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
