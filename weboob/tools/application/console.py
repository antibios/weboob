# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Christophe Benz, Romain Bignon
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


from copy import deepcopy
import getpass
import logging
import sys

from weboob.capabilities.account import ICapAccount, Account, AccountRegisterError
from weboob.core.backendscfg import BackendAlreadyExists
from weboob.core.modules import ModuleLoadError
from weboob.tools.browser import BrowserUnavailable, BrowserIncorrectPassword
from weboob.tools.value import Value, ValueBool, ValueFloat, ValueInt

from .base import BackendNotFound, BaseApplication

class BackendNotGiven(Exception):
    pass

class ConsoleApplication(BaseApplication):
    """
    Base application class for CLI applications.
    """

    CAPS = None

    # shell escape strings
    if sys.platform == 'win32':
        #workaround to disable bold
        BOLD   = ''
        NC     = ''          # no color
    else:
        BOLD   = '[1m'
        NC     = '[0m'    # no color

    stdin = sys.stdin
    stdout = sys.stdout

    def __init__(self, option_parser=None):
        BaseApplication.__init__(self, option_parser)
        self.enabled_backends = set()

    def unload_backends(self, *args, **kwargs):
        unloaded = self.weboob.unload_backends(*args, **kwargs)
        for backend in unloaded.itervalues():
            try:
                self.enabled_backends.remove(backend)
            except KeyError:
                pass
        return unloaded

    def is_backend_loadable(self, backend):
        return self.CAPS is None or self.caps_included(backend.iter_caps(), self.CAPS.__name__)

    def load_backends(self, *args, **kwargs):
        if 'errors' in kwargs:
            errors = kwargs['errors']
        else:
            kwargs['errors'] = errors = []
        ret = super(ConsoleApplication, self).load_backends(*args, **kwargs)

        for err in errors:
            print >>sys.stderr, 'Error(%s): %s' % (err.backend_name, err)
            if self.ask('Do you want to reconfigure this backend?', default=True):
                self.edit_backend(err.backend_name)
                self.load_backends(names=[err.backend_name])

        for name, backend in ret.iteritems():
            self.enabled_backends.add(backend)

        self.check_loaded_backends()

        return ret

    def check_loaded_backends(self, default_config=None):
        while len(self.enabled_backends) == 0:
            print 'Warning: there is currently no configured backend for %s' % self.APPNAME
            if not self.ask('Do you want to configure backends?', default=True):
                return False

            self.prompt_create_backends(default_config)

        return True

    def prompt_create_backends(self, default_config=None):
        self.weboob.modules_loader.load_all()
        r = ''
        while r != 'q':
            backends = []
            print '\nAvailable backends:'
            for name, backend in sorted(self.weboob.modules_loader.loaded.iteritems()):
                if not self.is_backend_loadable(backend):
                    continue
                backends.append(name)
                loaded = ' '
                for bi in self.weboob.iter_backends():
                    if bi.NAME == name:
                        if loaded == ' ':
                            loaded = 'X'
                        elif loaded == 'X':
                            loaded = 2
                        else:
                            loaded += 1
                print '%s%d)%s [%s] %s%-15s%s   %s' % (self.BOLD, len(backends), self.NC, loaded,
                                                       self.BOLD, name, self.NC, backend.description)
            print '%sq)%s --stop--\n' % (self.BOLD, self.NC)
            r = self.ask('Select a backend to add (q to stop)', regexp='^(\d+|q)$')

            if r.isdigit():
                i = int(r) - 1
                if i < 0 or i >= len(backends):
                    print 'Error: %s is not a valid choice' % r
                    continue
                name = backends[i]
                try:
                    inst = self.add_backend(name, default_config)
                    if inst:
                        self.load_backends(names=[inst])
                except (KeyboardInterrupt, EOFError):
                    print '\nAborted.'

            print 'Right right!'

    def _handle_options(self):
        self.load_default_backends()

    def load_default_backends(self):
        """
        By default loads all backends.

        Applications can overload this method to restrict backends loaded.
        """
        self.load_backends(self.CAPS)

    @classmethod
    def run(klass, args=None):
        try:
            super(ConsoleApplication, klass).run(args)
        except BackendNotFound, e:
            logging.error(e)

    def do(self, function, *args, **kwargs):
        if not 'backends' in kwargs:
            kwargs['backends'] = self.enabled_backends
        return self.weboob.do(function, *args, **kwargs)

    def parse_id(self, _id, unique_backend=False):
        try:
            _id, backend_name = _id.rsplit('@', 1)
        except ValueError:
            backend_name = None
        if unique_backend and not backend_name:
            backends = []
            for name, backend in sorted(self.weboob.modules_loader.loaded.iteritems()):
                if self.CAPS and not self.caps_included(backend.iter_caps(), self.CAPS.__name__):
                    continue
                backends.append((name, backend))
            if self.interactive:
                while not backend_name:
                    print 'This command works with a unique backend. Availables:'
                    for index, (name, backend) in enumerate(backends):
                        print '%s%d)%s %s%-15s%s   %s' % (self.BOLD, index + 1, self.NC, self.BOLD, name, self.NC,
                            backend.description)
                    response = self.ask('Select a backend to proceed', regexp='^\d+$')
                    if response.isdigit():
                        i = int(response) - 1
                        if i < 0 or i >= len(backends):
                            print 'Error: %s is not a valid choice' % response
                            continue
                        backend_name = backends[i][0]
            else:
                raise BackendNotGiven('Please specify a backend to use for this argument (%s@backend_name). '
                    'Availables: %s.' % (_id, ', '.join(name for name, backend in backends)))
        return _id, backend_name

    def caps_included(self, modcaps, caps):
        modcaps = [x.__name__ for x in modcaps]
        if not isinstance(caps, (list,set,tuple)):
            caps = (caps,)
        for cap in caps:
            if not cap in modcaps:
                return False
        return True

    # user interaction related methods

    def register_backend(self, name, ask_add=True):
        try:
            backend = self.weboob.modules_loader.get_or_load_module(name)
        except ModuleLoadError, e:
            backend = None

        if not backend:
            print 'Backend "%s" does not exist.' % name
            return None

        if not backend.has_caps(ICapAccount) or backend.klass.ACCOUNT_REGISTER_PROPERTIES is None:
            print 'You can\'t register a new account with %s' % name
            return None

        account = Account()
        account.properties = {}
        if backend.website:
            website = 'on website %s' % backend.website
        else:
            website = 'with backend %s' % backend.name
        while 1:
            asked_config = False
            for key, prop in backend.klass.ACCOUNT_REGISTER_PROPERTIES.iteritems():
                if not asked_config:
                    asked_config = True
                    print 'Configuration of new account %s' % website
                    print '-----------------------------%s' % ('-' * len(website))
                p = deepcopy(prop)
                p.set_value(self.ask(prop, default=account.properties[key].value if (key in account.properties) else prop.default))
                account.properties[key] = p
            if asked_config:
                print '-----------------------------%s' % ('-' * len(website))
            try:
                backend.klass.register_account(account)
            except AccountRegisterError, e:
                print u'%s' % e
                if self.ask('Do you want to try again?', default=True):
                    continue
                else:
                    return None
            else:
                break
        backend_config = {}
        for key, value in account.properties.iteritems():
            if key in backend.config:
                backend_config[key] = value.value

        if ask_add and self.ask('Do you want to add the new register account?', default=True):
            return self.add_backend(name, backend_config, ask_register=False)

        return backend_config

    def edit_backend(self, name, params=None):
        return self.add_backend(name, params, True)

    def add_backend(self, name, params=None, edit=False, ask_register=True):
        if params is None:
            params = {}

        if not edit:
            try:
                backend = self.weboob.modules_loader.get_or_load_module(name)
            except ModuleLoadError:
                backend = None
        else:
            bname, items = self.weboob.backends_config.get_backend(name)
            try:
                backend = self.weboob.modules_loader.get_or_load_module(bname)
            except ModuleLoadError:
                backend = None
            items.update(params)
            params = items
        if not backend:
            print 'Backend "%s" does not exist. Hint: use the "backends" command.' % name
            return None

        # ask for params non-specified on command-line arguments
        asked_config = False
        for key, value in backend.config.iteritems():
            if not asked_config:
                asked_config = True
                print 'Configuration of backend'
                print '------------------------'
            if key not in params or edit:
                params[key] = self.ask(value, default=params[key] if (key in params) else value.default)
            else:
                print u' [%s] %s: %s' % (key, value.description, '(masked)' if value.masked else params[key])
        if asked_config:
            print '------------------------'

        try:
            self.weboob.backends_config.add_backend(name, name, params, edit=edit)
            print 'Backend "%s" successfully %s.' % (name, 'updated' if edit else 'added')
            return name
        except BackendAlreadyExists:
            print 'Backend "%s" is already configured in file "%s"' % (name, self.weboob.backends_config.confpath)
            while self.ask('Add new instance of "%s" backend?' % name, default=False):
                new_name = self.ask('Please give new instance name (could be "%s_1")' % name, regexp=r'^[\w\-_]+$')
                try:
                    self.weboob.backends_config.add_backend(new_name, name, params)
                    print 'Backend "%s" successfully added.' % new_name
                    return new_name
                except BackendAlreadyExists:
                    print 'Instance "%s" already exists for backend "%s".' % (new_name, name)

    def ask(self, question, default=None, masked=False, regexp=None, choices=None):
        """
        Ask a question to user.

        @param question  text displayed (str)
        @param default  optional default value (str)
        @param masked  if True, do not show typed text (bool)
        @param regexp  text must match this regexp (str)
        @param choices  choices to do (list)
        @return  entered text by user (str)
        """

        if isinstance(question, Value):
            v = deepcopy(question)
            if default:
                v.default = default
            if masked:
                v.masked = masked
            if regexp:
                v.regexp = regexp
            if choices:
                v.choices = choices
        else:
            if isinstance(default, bool):
                klass = ValueBool
            elif isinstance(default, float):
                klass = ValueFloat
            elif isinstance(default, (int,long)):
                klass = ValueInt
            else:
                klass = Value

            v = klass(label=question, default=default, masked=masked, regexp=regexp, choices=choices)

        question = v.label
        if v.id:
            question = u'[%s] %s' % (v.id, question)

        aliases = {}
        if isinstance(v, ValueBool):
            question = u'%s (%s/%s)' % (question, 'Y' if v.default else 'y', 'n' if v.default else 'N')
        elif v.choices:
            tiny = True
            for key in v.choices.iterkeys():
                if len(key) > 5 or ' ' in key:
                    tiny = False
                    break

            if tiny:
                question = u'%s (%s)' % (question, '/'.join((s.upper() if s == v.default else s)
                                                            for s in (v.choices.iterkeys())))
            else:
                for n, (key, value) in enumerate(v.choices.iteritems()):
                    print '%s%2d)%s %s' % (self.BOLD, n + 1, self.NC, value)
                    aliases[str(n + 1)] = key
                question = u'%s (choose in list)' % question
        elif default not in (None, '') and not v.masked:
            question = u'%s [%s]' % (question, v.default)

        if v.masked:
            question = u'%s (hidden input)' % question

        question += ': '

        while True:
            if v.masked:
                if sys.platform == 'win32':
                    line = getpass.getpass(str(question))
                else:
                    line = getpass.getpass(question)
            else:
                self.stdout.write(question)
                self.stdout.flush()
                line = self.stdin.readline()
                if len(line) == 0:
                    raise EOFError()
                else:
                    line = line.rstrip('\r\n')

            if not line and v.default is not None:
                line = v.default
            if isinstance(line, str):
                line = line.decode('utf-8')

            if line in aliases:
                line = aliases[line]

            try:
                v.set_value(line)
            except ValueError, e:
                print 'Error: %s' % e
            else:
                break

        return v.value

    def bcall_error_handler(self, backend, error, backtrace):
        """
        Handler for an exception inside the CallErrors exception.

        This method can be overrided to support more exceptions types.
        """
        if isinstance(error, BrowserIncorrectPassword):
            msg = unicode(error)
            if not msg:
                msg = 'invalid login/password.'
            print >>sys.stderr, 'Error(%s): %s' % (backend.name, msg)
            if self.ask('Do you want to reconfigure this backend?', default=True):
                self.unload_backends(names=[backend.name])
                self.edit_backend(backend.name)
                self.load_backends(names=[backend.name])
        elif isinstance(error, BrowserUnavailable):
            msg = unicode(error)
            if not msg:
                msg = 'website is unavailable.'
            print >>sys.stderr, u'Error(%s): %s' % (backend.name, msg)
        elif isinstance(error, NotImplementedError):
            print >>sys.stderr, u'Error(%s): this feature is not supported yet by this backend.' % backend.name
            print >>sys.stderr, u'      %s   To help the maintainer of this backend implement this feature,' % (' ' * len(backend.name))
            print >>sys.stderr, u'      %s   please contact: %s <%s>' % (' ' * len(backend.name), backend.MAINTAINER, backend.EMAIL)
        else:
            print >>sys.stderr, u'Error(%s): %s' % (backend.name, error)
            if logging.root.level == logging.DEBUG:
                print >>sys.stderr, backtrace
            else:
                return True

    def bcall_errors_handler(self, errors):
        """
        Handler for the CallErrors exception.
        """
        ask_debug_mode = False
        for backend, error, backtrace in errors.errors:
            if self.bcall_error_handler(backend, error, backtrace):
                ask_debug_mode = True

        if ask_debug_mode:
            if self.interactive:
                print >>sys.stderr, 'Use "logging debug" option to print backtraces.'
            else:
                print >>sys.stderr, 'Use --debug option to print backtraces.'
