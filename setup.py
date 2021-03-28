import os
import sys
from setuptools import setup, Extension

from smbpi.version import __version__

dpmem_direct_ext = Extension('smbpi.dpmem_direct_ext',
                             sources = ['smbpi/dpmem_direct_ext.c'],
                             libraries = ['wiringPi'])

wd37c65_direct_ext = Extension('smbpi.wd37c65_direct_ext',
                             sources = ['smbpi/wd37c65_direct_ext.c', 'smbpi/micros.c'],
                             libraries = ['wiringPi'])

realtime_ext = Extension('smbpi.realtime_ext',
                             sources = ['smbpi/realtime_ext.c'],
                             libraries = [])                             

setup_result = setup(name='smbpi',
      version=__version__,
      description="Scott Baker's Raspberry Pi Library",
      packages=['smbpi'],
      zip_safe=False,
      ext_modules=[dpmem_direct_ext, wd37c65_direct_ext, realtime_ext]
     )
