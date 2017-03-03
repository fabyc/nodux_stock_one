#! -*- coding: utf8 -*-

from decimal import Decimal
from datetime import datetime
from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from trytond.pyson import Bool, Eval, Not, If, PYSONEncoder, Id
from trytond.wizard import (Wizard, StateView, StateAction, StateTransition,
    Button)
from trytond.modules.company import CompanyReport
from trytond.pyson import If, Eval, Bool, PYSONEncoder, Id
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.report import Report
conversor = None
try:
    from numword import numword_es
    conversor = numword_es.NumWordES()
except:
    print("Warning: Does not possible import numword module!")
    print("Please install it...!")
import pytz
from datetime import datetime,timedelta
import time


__all__ = ['PrintReportStockStart', 'PrintReportStock', 'ReportStock']

_ZERO = Decimal(0)

class PrintReportStockStart(ModelView):
    'Print Report Products Start'
    __name__ = 'nodux_stock_one.print_report_stock.start'

    company = fields.Many2One('company.company', 'Company', required=True)
    all_products = fields.Boolean("All products", states={
        'readonly' : Eval('greater_zero', True),
    })
    greater_zero = fields.Boolean("Greater than zero", states={
        'readonly' : Eval('all_products', True),
    })

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_all_products():
        return True

    @staticmethod
    def default_greater_zero():
        return False

    @fields.depends('all_products', 'greater_zero')
    def on_change_all_products(self):
        res = {}
        if self.all_products == True:
            res['greater_zero'] = False
        return res

    @fields.depends('all_products', 'greater_zero')
    def on_change_greater_zero(self):
        res = {}
        if self.greater_zero == True:
            res['all_products'] = False
        return res

class PrintReportStock(Wizard):
    'Print Report Products'
    __name__ = 'nodux_stock_one.print_report_stock'
    start = StateView('nodux_stock_one.print_report_stock.start',
        'nodux_stock_one.print_stock_report_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('nodux_stock_one.report_stocks')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'all_products' : self.start.all_products,
            'greater_zero' : self.start.greater_zero,
            }
        return action, data

    def transition_print_(self):
        return 'end'

class ReportStock(Report):
    __name__ = 'nodux_stock_one.report_stocks'

    @classmethod
    def parse(cls, report, records, data, localcontext):
        pool = Pool()
        User = pool.get('res.user')
        user = User(Transaction().user)
        Date = pool.get('ir.date')
        Company = pool.get('company.company')
        Product = pool.get('product.template')
        company = Company(data['company'])
        all_products = data['all_products']
        greater_zero = data['greater_zero']

        if all_products == True:
            products = Product.search([('id','>', 0)])
        else:
            products = Product.search([('total','>', 0)])

        if company.timezone:
            timezone = pytz.timezone(company.timezone)
            dt = datetime.now()
            hora = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)
        else:
            company.raise_user_error('Configure la zona Horaria de la empresa')

        localcontext['company'] = company
        localcontext['hora'] = hora.strftime('%H:%M:%S')
        localcontext['fecha_im'] = hora.strftime('%d/%m/%Y')
        localcontext['products'] = products
        return super(ReportStock, cls).parse(report, records, data,
                localcontext=localcontext)
