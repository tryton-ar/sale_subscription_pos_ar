# This file is part sale_subscription_pos_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool

from . import subscription


def register():
    Pool.register(
        subscription.Subscription,
        module='sale_subscription_pos_ar', type_='model')
