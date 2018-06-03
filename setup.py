import os
import sys
from setuptools import setup

from smbpi.version import __version__

setup_result = setup(name='smbpi',
      version=__version__,
      description="Scott Baker's Raspberry Pi Library",
      packages=['smbpi'],
      zip_safe=False,
     )
