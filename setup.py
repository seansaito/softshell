from setuptools import setup

setup(name='softshell',
      version='0.1',
      description='Change hard-coded variables into dynamic ones without refactoring',
      url='http://github.com/seansaito/softshell',
      author='Sean Saito',
      author_email='saitosean@ymail.com',
      license='MIT',
      packages=['softshell'],
      install_requires=[
          "PyYAML>=5.1"
      ],
      scripts=['bin/softshell'],
      zip_safe=False)
