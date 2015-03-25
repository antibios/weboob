# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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


import lxml.html as html

from weboob.tools.compat import basestring, unicode, urljoin
from weboob.tools.html import html2text

from .standard import _NO_DEFAULT, Filter, FilterError, _Selector

__all__ = ['CSS', 'XPath', 'XPathNotFound', 'AttributeNotFound',
           'Attr', 'Link', 'CleanHTML', 'FormValue']


class XPathNotFound(FilterError):
    pass


class AttributeNotFound(FilterError):
    pass


class CSS(_Selector):
    def select(self, selector, item):
        ret = item.cssselect(selector)
        if isinstance(ret, list):
            for el in ret:
                if isinstance(el, html.HtmlElement):
                    self.highlight_el(el, item)

        return ret


class XPath(_Selector):
    pass


class Attr(Filter):
    def __init__(self, selector, attr, default=_NO_DEFAULT):
        super(Attr, self).__init__(selector, default=default)
        self.attr = attr

    def filter(self, el):
        try:
            return u'%s' % el[0].attrib[self.attr]
        except IndexError:
            return self.default_or_raise(XPathNotFound('Unable to find element %s' % self.selector))
        except KeyError:
            return self.default_or_raise(AttributeNotFound('Element %s does not have attribute %s' % (el[0], self.attr)))


class Link(Attr):
    """
    Get the link uri of an element.

    If the <a> tag is not found, an exception IndexError is raised.
    """

    def __init__(self, selector=None, default=_NO_DEFAULT):
        super(Link, self).__init__(selector, 'href', default=default)


class AbsoluteLink(Link):
    def __call__(self, item):
        ret = super(AbsoluteLink, self).__call__(item)
        if ret:
            ret = urljoin(item.page.url, ret)
        return ret


class CleanHTML(Filter):
    def filter(self, txt):
        if isinstance(txt, (tuple, list)):
            return u' '.join([self.clean(item) for item in txt])
        return self.clean(txt)

    @classmethod
    def clean(cls, txt):
        if not isinstance(txt, basestring):
            txt = html.tostring(txt, encoding=unicode)
        return html2text(txt)


class UnrecognizedElement(Exception):
    pass


class FormValue(Filter):
    """
    Extract a Python value from a form element.
    Checkboxes and radio return booleans, while the rest
    return text. Select returns the user-visible text.
    """
    def filter(self, el):
        try:
            el = el[0]
        except IndexError:
            return self.default_or_raise(XPathNotFound('Unable to find element %s' % self.selector))
        if el.tag == 'input':
            # checkboxes or radios
            if el.attrib.get('type') in ('radio', 'checkbox'):
                return 'checked' in el.attrib
            # regular text input
            elif el.attrib.get('type', '') in ('', 'text', 'email', 'search', 'tel', 'url'):
                try:
                    return unicode(el.attrib['value'])
                except KeyError:
                    return self.default_or_raise(AttributeNotFound('Element %s does not have attribute value' % el))
            # TODO handle html5 number, datetime, etc.
            else:
                raise UnrecognizedElement('Element %s is recognized' % el)
        elif el.tag == 'textarea':
            return unicode(el.text)
        elif el.tag == 'select':
            options = el.xpath('.//option[@selected]')
            # default is the first one
            if len(options) == 0:
                options = el.xpath('.//option[1]')
            return u'\n'.join([unicode(o.text) for o in options])
        else:
            raise UnrecognizedElement('Element %s is recognized' % el)
