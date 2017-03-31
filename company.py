#! -*- coding: utf8 -*-

import string
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta
import hashlib
import base64

__all__ = ['Company']
__metaclass__ = PoolMeta

class Company():
    'Company'
    __name__ = 'company.company'

    sequence_stock = fields.Integer('Sequence Stock')
    sequence_stock_out = fields.Integer('Sequence Stock Out')

    @classmethod
    def __setup__(cls):
        super(Company, cls).__setup__()

    @staticmethod
    def default_sequence_stock():
        return 1

    @staticmethod
    def default_sequence_stock_out():
        return 1
