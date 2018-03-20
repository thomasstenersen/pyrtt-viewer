from setuptools import setup


setup(
    name="pyrtt-viewer",
    author="Thomas Stenersen",
    author_email="stenersen.thomas@gmail.com",
    url="https://github.com/thomasstenersen/pyrtt-viewer",
    version="0.1.1",
    description="A simple script for RTT I/O",
    install_requires=["pynrfjprog"],
    python_requires=">=3",
    scripts=["pyrtt-viewer"]
)
