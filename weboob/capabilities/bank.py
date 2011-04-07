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


from datetime import datetime, date

from .base import IBaseCap, CapBaseObject


__all__ = ['Account', 'AccountNotFound', 'TransferError', 'ICapBank', 
    'Operation']


class AccountNotFound(Exception):
    def __init__(self, msg=None):
        if msg is None:
            msg = 'Account not found'
        Exception.__init__(self, msg)

class TransferError(Exception):
    pass

class Account(CapBaseObject):
    def __init__(self):
        CapBaseObject.__init__(self, 0)
        self.add_field('label', basestring)
        self.add_field('balance', float)
        self.add_field('coming', float)
        self.link_id = None

    def __repr__(self):
        return u"<Account id=%r label=%r>" % (self.id, self.label)


class Operation(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('date', (basestring, datetime, date))
        self.add_field('label', unicode)
        self.add_field('amount', float)

    def __repr__(self):
        return "<Operation date='%s' label='%s' amount=%s>" % (self.date, 
            self.label, self.amount)

class Transfer(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('amount', float)
        self.add_field('date', (basestring, datetime, date))
        self.add_field('origin', (int, long, basestring))
        self.add_field('recipient', (int, long, basestring))

class ICapBank(IBaseCap):
    def iter_accounts(self):
        raise NotImplementedError()

    def get_account(self, _id):
        raise NotImplementedError()

    def iter_operations(self, account):
        raise NotImplementedError()

    def iter_history(self, account):
        raise NotImplementedError()

    def transfer(self, account, to, amount, reason=None):
        """
        Make a transfer from an account to a recipient.

        @param account [Account]  account to take money
        @param to [Account]  account to send money
        @param amount [float]  amount
        @param reason [str]  reason of transfer
        @return [Transfer]  a Transfer object
        """
        raise NotImplementedError()
