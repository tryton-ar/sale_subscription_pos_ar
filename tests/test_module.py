# The COPYRIGHT file at the top level of this repository contains the
# full copyright notices and license terms.

from trytond.modules.company.tests import CompanyTestMixin
from trytond.tests.test_tryton import ModuleTestCase


class SaleSubscriptionPosArTestCase(CompanyTestMixin, ModuleTestCase):
    'SaleSubscriptionPosArTestCase'
    module = 'sale_subscription_pos_ar'


del ModuleTestCase
