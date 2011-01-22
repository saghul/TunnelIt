#!/usr/bin/env python
# coding=utf8

# Copyright (C) 2011 Saúl Ibarra Corretgé <saghul@gmail.com>
#

import os

from distutils.core import setup

from tunnelit import __version__


def find_packages(toplevel):
    return [directory.replace(os.path.sep, '.') for directory, subdirs, files in os.walk(toplevel) if '__init__.py' in files]

setup(name         = "tunnelit",
      version      = __version__,
      author       = "Saúl Ibarra Corretgé (saghul)",
      author_email = "saghul@gmail.com",
      url          = "http://github.com/saghul/tunnelit",
      description  = "TunnelIt - A simple reverse SSH forwarder",
      license      = "GPLv3",
      packages     = find_packages('tunnelit'),
      scripts      = ['tunnelit-server'],
      data_files   = [('/etc/tunnelit/keys', [])]
      )

