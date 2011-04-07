# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from unittest import TestCase
from nose.plugins.skip import SkipTest
from weboob.core import Weboob
from random import choice


__all__ = ['TestCase', 'BackendTest']

class BackendTest(TestCase):
    BACKEND = None

    def __init__(self, *args, **kwargs):
        TestCase.__init__(self, *args, **kwargs)

        self.backend = None
        self.weboob = Weboob()

        if self.weboob.load_backends(modules=[self.BACKEND]):
            self.backend = choice(self.weboob.backend_instances.values())

    def run(self, result):
        try:
            if not self.backend:
                result.startTest(self)
                result.stopTest(self)
                raise SkipTest()

            return TestCase.run(self, result)
        finally:
            self.weboob.deinit()
