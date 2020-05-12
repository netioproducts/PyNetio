import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Netio",
    version="0.0.6",
    author="Adam Verner",
    author_email="averner@netio.eu",
    license="MIT",
    description="Interface to control NETIO Products devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/netioproducts/PyNetio",
    install_requires=[
        "requests>=2.23",
        "pyOpenSSL>=19.0"
    ],
    packages=["Netio"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.6",
    ],
    python_requires='>=3.6',
)
