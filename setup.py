import os
import sys
import subprocess
import shutil

from distutils.sysconfig import get_python_lib
from setuptools import setup

VERSION = "0.0.1"

def fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join)
    in a platform-neutral way.
    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)


EXCLUDE_FROM_PACKAGES = []

def is_package(package_name):
    for pkg in EXCLUDE_FROM_PACKAGES:
        if package_name.startswith(pkg):
            return False
    return True

# Compile the list of packages available, because distutils doesn't have
# an easy way to do this.
packages, package_data = [], {}

root_dir = os.path.dirname(__file__)
if root_dir != '':
    os.chdir(root_dir)
cactus_dir = 'wufoo'

for dirpath, dirnames, filenames in os.walk(cactus_dir):
    # Ignore PEP 3147 cache dirs and those whose names start with '.'
    dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
    parts = fullsplit(dirpath)
    package_name = '.'.join(parts)
    if '__init__.py' in filenames and is_package(package_name):
        packages.append(package_name)
    elif filenames:
        relative_path = []
        while '.'.join(parts) not in packages:
            relative_path.append(parts.pop())
        relative_path.reverse()
        path = os.path.join(*relative_path)
        package_files = package_data.setdefault('.'.join(parts), [])
        package_files.extend([os.path.join(path, f) for f in filenames])


setup(
    name='Wufoo',
    version=VERSION,
    description="Quick and dirty Wufoo-based HTML form manager",
    long_description=open('README.md').read(),
    url='http://github.com/krallin/wufoo',
    author='Thomas Orozco',
    author_email='thomas@orozco.fr',
    license='MIT',
    packages=packages,
    package_data=package_data,
    entry_points={},
    install_requires=["requests", "beautifulsoup4"],
    extras_require={},
    zip_safe=True,
    setup_requires=[],
    tests_require=[],
    classifiers=[],
)
