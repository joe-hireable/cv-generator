from setuptools import setup, find_packages

setup(
    name="cv-generator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "functions-framework==3.4.0",
        "docxtpl==0.16.7",
        "requests==2.31.0",
        "google-cloud-storage==2.13.0",
        "google-cloud-secretmanager==2.16.3",
        "pydantic==2.5.2",
        "jsonschema==4.20.0"
    ],
) 