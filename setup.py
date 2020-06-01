import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Netio",
    version="1.0.3",
    author="Adam Verner",
    author_email="averner@netio.eu",
    license="MIT",
    description="Interface to control NETIO Products devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/netioproducts/PyNetio",
    install_requires=["requests>=2.23", "pyOpenSSL>=19.0", 'wheel'],
    packages=["Netio"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: Developers",
        "Natural Language :: English",
    ],
    python_requires='>=3.6',
    entry_points={'console_scripts': ['Netio=Netio.cli:main']},
)
