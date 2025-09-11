#!/usr/bin/env python3
"""
Setup script for PyLLRP - Pure Python LLRP implementation
"""

from setuptools import setup, find_packages
import os

# Read version from __init__.py
def get_version():
    init_file = os.path.join(os.path.dirname(__file__), 'llrp', '__init__.py')
    with open(init_file, 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return '0.1.0'

# Read README
def get_long_description():
    readme_file = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_file):
        with open(readme_file, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

setup(
    name='pyllrp',
    version=get_version(),
    description='Pure Python LLRP (Low Level Reader Protocol) implementation',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    author='PyLLRP Contributors',
    author_email='',
    url='https://github.com/your-username/pyllrp',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    install_requires=[
        # No external dependencies!
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'black>=21.0',
            'flake8>=3.8',
        ],
    },
    entry_points={
        'console_scripts': [
            'llrp-example=llrp.example:main',
        ],
    },
    keywords='llrp rfid epcglobal reader protocol impinj',
    project_urls={
        'Bug Reports': 'https://github.com/your-username/pyllrp/issues',
        'Source': 'https://github.com/your-username/pyllrp',
        'Documentation': 'https://github.com/your-username/pyllrp/wiki',
    },
)