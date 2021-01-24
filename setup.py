#!/usr/bin/env python3
import setuptools

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="Activate-App",
    version="0.0.1",
    author="Tom Fryers",
    description="Activate is a free activity log and analysis tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/Tom_Fryers/activate",
    packages=setuptools.find_packages(),
    entry_points={"gui_scripts": "activate = activate.app:main"},
    include_package_data=True,
    package_data={"activate.resources": ["/".join("*" * i) for i in range(9)]},
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.6",
)
