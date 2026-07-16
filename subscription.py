# This file is part sale_subscription_pos_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from decimal import Decimal
from datetime import date as pdate
from calendar import monthrange
from trytond.i18n import gettext
from trytond.bus import notify
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.exceptions import UserError
from trytond.modules.account_invoice_ar.invoice import INVOICE_TYPE_AFIP_CODE


class Subscription(metaclass=PoolMeta):
    __name__ = 'sale.subscription'

    pos = fields.Many2One('account.pos', 'Point of Sale',
        domain=[
            ('company', '=', Eval('company', -1)),
            ('pos_daily_report', '=', False),
        ],
        states={'readonly': Eval('state') != 'draft'})

    @classmethod
    def default_pos(cls):
        Configuration = Pool().get('sale.configuration')
        config = Configuration(1)
        if config.pos:
            return config.pos.id

    def _get_invoice(self):
        invoice = super()._get_invoice()
        if invoice:
            invoice.pos = self.pos
            invoice.invoice_type = self._get_invoice_type()
            invoice.invoice_date = None
            invoice.pyafipws_concept = self._get_pyafipws_concept()
            invoice.pyafipws_billing_start_date, invoice.pyafipws_billing_end_date = self._get_pyafipws_billing_dates()

        return invoice

    def _get_pyafipws_concept(self):
        '''
        returns pyafipws_concept (service).
        '''
        return '2'

    def _get_pyafipws_billing_dates(self):
        '''
        get pyafipws_billing_dates by next_invoice_date.
        '''
        if self.next_invoice_date:
            year = int(self.next_invoice_date.strftime("%Y"))
            month = int(self.next_invoice_date.strftime("%m"))
        else:
            today = Pool().get('ir.date').today()
            year = int(today.strftime("%Y"))
            month = int(today.strftime("%m"))

        return [
            pdate(year, month, 1),
            pdate(year, month, monthrange(year, month)[1])
        ]

    def _get_invoice_type(self):
        '''
        Set invoice type field.
        require: pos field must be set first.
        '''
        pool = Pool()
        PosSequence = pool.get('account.pos.sequence')

        if not self.pos or not self.party:
            return None

        company_iva = (self.company.party and
            self.company.party.iva_condition or None)
        client_iva = self.party and self.party.iva_condition or None
        credit_note = False
        fce = False

        if company_iva == 'responsable_inscripto':
            if not client_iva:
                return None
            if client_iva in ('responsable_inscripto', 'monotributo'):
                kind = 'A'
            elif client_iva == 'cliente_exterior':
                kind = 'E'
            else:
                kind = 'B'
        else:
            if client_iva == 'cliente_exterior':
                kind = 'E'
            else:
                kind = 'C'

        invoice_type, invoice_type_desc = INVOICE_TYPE_AFIP_CODE[
            ('out', credit_note, kind, fce)
            ]
        sequences = PosSequence.search([
            ('pos', '=', self.pos),
            ('invoice_type', '=', invoice_type)
            ])
        if len(sequences) == 0:
            raise UserError(gettext(
                'account_invoice_ar.msg_missing_sequence',
                invoice_type=invoice_type_desc))
        elif len(sequences) > 1:
            raise UserError(gettext(
                'account_invoice_ar.msg_too_many_sequences',
                invoice_type_desc))
        else:
            sequence, = sequences
        return sequence.id
