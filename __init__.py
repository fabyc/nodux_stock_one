from trytond.pool import Pool
from .stock import *

def register():
    Pool.register(
        PrintReportStockStart,
        module='nodux_stock_one', type_='model')
    Pool.register(
        PrintReportStock,
        module='nodux_stock_one', type_='wizard')
    Pool.register(
        ReportStock,
        module='nodux_stock_one', type_='report')
