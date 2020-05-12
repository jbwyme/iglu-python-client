import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="iglu-client",
    version="0.2.0",
    author="Josh Wymer",
    author_email="josh@mixpanel.com",
    description="A python client for retrieving Iglu schemas and validating self-describing JSON",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jbwyme/iglu-python-client",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
