import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='tomatoslicer',
    version='0.8.2',
    author='Alan Stockwell',
    author_email='alan@stockwell.nz',
    description='A solution to all my myriad time slicing needs. Time math is anathema to sanity',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/alanstockwell/tomatoslicer',
    packages=setuptools.find_packages(),
    install_requires=[
          'python-dateutil',
      ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
