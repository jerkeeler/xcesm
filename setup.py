from setuptools import setup, find_packages

setup(name='xcesm',
      version='0.01',
      description='xarray plugin for CESM output diagnosis.',
      url='https://github.com/Yefee/xcesm',
      author='Chengfei He',
      author_email='che43@wisc.edu',
      include_package_data=True,
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        ],
      keywords='climate modeling modelling model gcm',
      license='MIT',
      # packages=['xcesm','config'],
      packages=find_packages(),
      package_data={'xcesm': ['config/*.nc', 'plots/*.json']},
      install_requires=['xarray', 'pyresample', 'cartopy'],
      zip_safe=False)
print(find_packages())
