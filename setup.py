import os
import sys
from setuptools import setup, Extension

from smbpi.version import __version__


dpmem_direct_ext = Extension('smbpi.dpmem_direct_ext',
                             sources = ['smbpi/dpmem_direct_ext.c'],
                             libraries = ['wiringPi'])

setup_result = setup(name='smbpi',
      version=__version__,
      description="Scott Baker's Raspberry Pi Library",
      packages=['smbpi'],
      zip_safe=False,
      ext_modules=[dpmem_direct_ext]
     )
