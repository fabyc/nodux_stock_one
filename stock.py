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


__all__ = ['Stock', 'StockLine', 'PrintReportStockStart', 'PrintReportStock',
'ReportStock']

_ZERO = Decimal(0)

class Stock(Workflow, ModelSQL, ModelView):
    'Stock'
    __name__ = 'stock.stock'
    _rec_name = 'reference'

    company = fields.Many2One('company.company', 'Company', required=True,
        states={
            'readonly': (Eval('state') != 'draft') | Eval('lines', [0]),
            },
        domain=[
            ('id', If(Eval('context', {}).contains('company'), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ],
        depends=['state'], select=True)
    reference = fields.Char('Number', readonly=True, select=True)
    description = fields.Char('Description',
        states={
            'readonly': Eval('state') != 'draft',
            },
        depends=['state'])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], 'State', readonly=True, required=True)
    stock_date = fields.Date('Stock Date', required= True,
        states={
            'readonly': ~Eval('state').in_(['draft']),
            },
        depends=['state'])

    lines = fields.One2Many('stock.line', 'stock', 'Lines', states={
            'readonly': Eval('state') != 'draft',
            },
        depends=['party', 'state'])

    @classmethod
    def __register__(cls, module_name):
        transaction = Transaction()
        cursor = transaction.connection.cursor()
        sql_table = cls.__table__()

        super(Stock, cls).__register__(module_name)
        cls._order.insert(0, ('stock_date', 'DESC'))
        cls._order.insert(1, ('id', 'DESC'))


    @classmethod
    def __setup__(cls):
        super(Stock, cls).__setup__()

        cls._transitions |= set((
                ('draft', 'done'),
                ))

        cls._buttons.update({
                'done': {
                    'invisible': Eval('state') != 'draft',
                    'readonly': ~Eval('lines', []),
                    },
                })

    @classmethod
    def delete(cls, stocks):
        for stock in stocks:
            if (stock.state == 'done'):
                cls.raise_user_error('No puede eliminar en inventario inicial %s,\nporque ya ha sido realizado',(stock.reference))
        super(Stock, cls).delete(stocks)

    @classmethod
    def copy(cls, stocks, default=None):
        if default is None:
            default = {}
        Date = Pool().get('ir.date')
        date = Date.today()

        default = default.copy()
        default['state'] = 'draft'
        default['reference'] = None
        default['stock_date'] = date
        #default.setdefault('', None)
        return super(Stock, cls).copy(stocks, default=default)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_state():
        return 'draft'

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def done(cls, stocks):
        for stock in stocks:
            cls.raise_user_warning('done%s' % stock.reference,
                   'Esta seguro de confirmar el inventario')
            if not stock.reference:
                Company = Pool().get('company.company')
                company = Company(Transaction().context.get('company'))

                reference = company.sequence_stock
                company.sequence_stock = company.sequence_stock + 1
                company.save()

                if len(str(reference)) == 1:
                    reference_end = 'II-00000000' + str(reference)
                elif len(str(reference)) == 2:
                    reference_end = 'II-0000000' + str(reference)
                elif len(str(reference)) == 3:
                    reference_end = 'II-000000' + str(reference)
                elif len(str(reference)) == 4:
                    reference_end = 'II-00000' + str(reference)
                elif len(str(reference)) == 5:
                    reference_end = 'II-0000' + str(reference)
                elif len(str(reference)) == 6:
                    reference_end = 'II-000' + str(reference)
                elif len(str(reference)) == 7:
                    reference_end = 'II-00' + str(reference)
                elif len(str(reference)) == 8:
                    reference_end = 'II-0' + str(reference)
                elif len(str(reference)) == 9:
                    reference_end = 'II-' + str(reference)

                stock.reference = str(reference_end)
                stock.save()

                for line in stock.lines:
                    product = line.product.template
                    if product.type == "goods":
                        if product.total == None:
                            product.total = Decimal(line.quantity)
                        else:
                            product.total = Decimal(line.product.template.total) + Decimal(line.quantity)
                        product.save()
        cls.write([s for s in stocks], {
                'state': 'done',
                })

class StockLine(ModelSQL, ModelView):
    'Stock Line'
    __name__ = 'stock.line'
    _rec_name = 'description'
    stock = fields.Many2One('stock.stock', 'Stock', ondelete='CASCADE',
        select=True)
    sequence = fields.Integer('Sequence')
    quantity = fields.Float('Quantity',
        digits=(16, Eval('unit_digits', 2)))
    product = fields.Many2One('product.product', 'Product')
    description = fields.Text('Description', size=None, required=True)

    @classmethod
    def __setup__(cls):
        super(StockLine, cls).__setup__()

        for fname in ('product', 'quantity'):
            field = getattr(cls, fname)
            if field.states.get('readonly'):
                del field.states['readonly']

    @staticmethod
    def default_stock():
        if Transaction().context.get('stock'):
            return Transaction().context.get('stock')
        return None

    @fields.depends('product', 'description')
    def on_change_product(self):
        Product = Pool().get('product.product')
        if self.product:
            self.description =  self.product.name


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
        if self.all_products == True:
            self.greater_zero = False

    @fields.depends('all_products', 'greater_zero')
    def on_change_greater_zero(self):
        if self.greater_zero == True:
            self.all_products = False


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
    def __setup__(cls):
        super(ReportStock, cls).__setup__()

    @classmethod
    def get_context(cls, records, data):
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

        report_context = super(ReportStock, cls).get_context(records, data)

        report_context['company'] = company
        report_context['hora'] = hora.strftime('%H:%M:%S')
        report_context['fecha_im'] = hora.strftime('%d/%m/%Y')
        report_context['products'] = products
        return report_context
