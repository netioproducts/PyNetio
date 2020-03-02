import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Netio", # Replace with your own username
    version="0.0.3",
    author="Adam Verner",
    author_email="averner@netio.eu",
    description="Interface to control NETIO Products devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/netioproducts/PyNetio",
    install_requires=[
        'requests'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.6",
        "Topic :: Other/Nonlisted Topic"
    ],
    python_requires='>=3.6',
)
