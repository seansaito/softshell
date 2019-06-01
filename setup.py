from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='softshell',
      version='0.1',
      description="Turn hard-coded variables into dynamic ones without refactoring.",
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='http://github.com/seansaito/softshell',
      author='Sean Saito',
      author_email='saitosean@ymail.com',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.6'
      ],
      license='MIT',
      packages=['softshell'],
      install_requires=[
          "PyYAML>=5.1"
      ],
      scripts=['bin/softshell'],
      zip_safe=False)
