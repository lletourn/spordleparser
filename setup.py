import setuptools
import os


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setuptools.setup(
    name='spordleparser'
    version=get_version("spordleparser/__init__.py"),
    description='Spordle parser',
    install_requires=[
            'beautifulsoup4 ~=4.0.0'
        ],
    python_requires='>=3.6',
    packages=setuptools.find_packages(),
)
