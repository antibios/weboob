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


from weboob.tools.browser import BasePage
from weboob.tools.parsers.lxmlparser import select


__all__ = ['PlayerPage']


class PlayerPage(BasePage):
    def get_current(self):
        title = select(self.document.getroot(), 'span.titre_en_cours', 1).text
        artist = select(self.document.getroot(), 'span.artiste_en_cours', 1).text
        return unicode(artist).strip(), unicode(title).strip()
