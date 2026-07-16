====================
Sale Subscription AR
====================

Imports::

    >>> import datetime
    >>> from decimal import Decimal

    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules, assertEqual
    >>> from trytond.modules.account.tests.tools import create_chart, create_fiscalyear
    >>> from trytond.modules.account_ar.tests.tools import get_accounts
    >>> from trytond.modules.currency.tests.tools import get_currency
    >>> from trytond.modules.company.tests.tools import create_company, get_company
    >>> from trytond.modules.account_invoice.tests.tools import set_fiscalyear_invoice_sequences
    >>> from trytond.modules.account_invoice_ar.tests.tools import \
    ...     create_pos, get_pos, get_invoice_types, get_tax
    >>> from trytond.tests.tools import activate_modules, assertEqual, assertTrue

Activate modules::

    >>> config = activate_modules('sale_subscription_pos_ar')

Create sale user::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')

    >>> sale_user = User()
    >>> sale_user.name = 'Sale'
    >>> sale_user.login = 'sale'
    >>> sale_group, = Group.find([('name', '=', 'Sales')])
    >>> sale_user.groups.append(sale_group)
    >>> sale_user.save()

Create product user::

    >>> product_user = User()
    >>> product_user.name = 'Product'
    >>> product_user.login = 'product'
    >>> product_group, = Group.find([('name', '=', 'Product Administration')])
    >>> product_user.groups.append(product_group)
    >>> product_user.save()

Create company::

    >>> currency = get_currency('ARS')
    >>> currency.afip_code = 'PES'
    >>> currency.save()
    >>> _ = create_company(currency=currency)
    >>> company = get_company()
    >>> tax_identifier = company.party.identifiers.new()
    >>> tax_identifier.type = 'ar_vat'
    >>> tax_identifier.code = '30710158254'  # gcoop CUIT
    >>> company.party.iva_condition = 'responsable_inscripto'
    >>> company.party.save()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]
    >>> period_ids = [p.id for p in fiscalyear.periods]

Create chart of accounts::

    >>> _ = create_chart(company, chart='account_ar.root_ar')
    >>> accounts = get_accounts(company)
    >>> account_receivable = accounts['receivable']
    >>> account_payable = accounts['payable']
    >>> account_revenue = accounts['revenue']
    >>> account_expense = accounts['expense']
    >>> account_tax = accounts['sale_tax']
    >>> account_cash = accounts['cash']

Create point of sale::

    >>> _ = create_pos(company)
    >>> pos = get_pos()
    >>> invoice_types = get_invoice_types()

Create taxes::

    >>> sale_tax = get_tax('IVA Ventas 21%')
    >>> sale_tax_nogravado = get_tax('IVA Ventas No Gravado')

Configure POS as default in sale configuration::

    >>> Configuration = Model.get('sale.configuration')
    >>> config_record = Configuration(1)
    >>> config_record.pos = pos
    >>> config_record.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer Test')
    >>> customer.iva_condition = 'responsable_inscripto'
    >>> customer.vat_number = '30688555872'
    >>> customer.account_receivable = account_receivable
    >>> customer.save()

Create subscription recurrence rule sets::

    >>> RecurrenceRuleSet = Model.get('sale.subscription.recurrence.rule.set')

    >>> monthly = RecurrenceRuleSet(name='Monthly')
    >>> rule, = monthly.rules
    >>> rule.freq = 'monthly'
    >>> rule.interval = 1
    >>> monthly.save()

    >>> daily = RecurrenceRuleSet(name='Daily')
    >>> rule, = daily.rules
    >>> rule.freq = 'daily'
    >>> rule.interval = 1
    >>> daily.save()

Create account category::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = account_expense
    >>> account_category.account_revenue = account_revenue
    >>> account_category.customer_taxes.append(sale_tax)
    >>> account_category.save()

Create subscription service::

    >>> Service = Model.get('sale.subscription.service')
    >>> ProductTemplate = Model.get('product.template')
    >>> Uom = Model.get('product.uom')

    >>> unit, = Uom.find([('name', '=', 'Unit')])

    >>> template = ProductTemplate()
    >>> template.name = 'Rental'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('10')
    >>> template.account_category = account_category
    >>> template.salable = True
    >>> template.save()
    >>> product, = template.products

Create service::

    >>> service = Service()
    >>> service.product = product
    >>> service.consumption_recurrence = daily
    >>> service.save()

Create subscription with POS::

    >>> Subscription = Model.get('sale.subscription')

    >>> subscription = Subscription()
    >>> subscription.party = customer
    >>> subscription.start_date = datetime.date(2016, 1, 1)
    >>> subscription.invoice_start_date = datetime.date(2016, 2, 1)
    >>> subscription.invoice_recurrence = monthly
    >>> line = subscription.lines.new()
    >>> line.service = service
    >>> line.quantity = 10
    >>> assertEqual(line.start_date, subscription.start_date)

Verify POS field is populated from sale.configuration::

    >>> subscription.pos == pos
    True

Create subscription quote::

    >>> subscription.click('quote')
    >>> subscription.state
    'quotation'

Run the subscription::

    >>> subscription.click('run')
    >>> subscription.state
    'running'
    >>> subscription.reload()
    >>> subscription.next_invoice_date
    datetime.date(2016, 2, 1)

Generate line consumption::

    >>> LineConsumption = Model.get('sale.subscription.line.consumption')

    >>> line_consumption_create = Wizard(
    ...     'sale.subscription.line.consumption.create')
    >>> line_consumption_create.form.date = datetime.date(2016, 1, 31)
    >>> line_consumption_create.execute('create_')

    >>> len(LineConsumption.find([]))
    31

    >>> subscription.reload()
    >>> line, = subscription.lines
    >>> line.next_consumption_date
    datetime.date(2016, 2, 1)

Create subscription invoice::

    >>> Invoice = Model.get('account.invoice')

    >>> create_invoice = Wizard('sale.subscription.create_invoice')
    >>> create_invoice.form.date = datetime.date(2016, 2, 1)
    >>> create_invoice.execute('create_')

Verify invoice created from subscription::

    >>> invoices = Invoice.find([])
    >>> len(invoices)
    1
    >>> invoice = invoices[0]
    >>> invoice.pos == pos
    True
    >>> invoice.invoice_type == invoice_types['1']
    True
    >>> invoice.party == customer
    True
    >>> invoice.pyafipws_concept == '2'
    True
    >>> invoice.pyafipws_billing_start_date
    datetime.date(2016, 2, 1)
    >>> invoice.pyafipws_billing_end_date
    datetime.date(2016, 2, 29)

Verify invoice lines from consumption::

    >>> len(invoice.lines) > 0
    True
    >>> line, = invoice.lines
    >>> line.quantity
    310.0
    >>> line.unit_price
    Decimal('10.0000')

Verify subscription next_invoice_date advanced::

    >>> subscription.reload()
    >>> subscription.next_invoice_date
    datetime.date(2016, 3, 1)

Post the invoice::

    >>> invoice.pyafipws_concept is not None
    True
    >>> invoice.invoice_date is None or invoice.invoice_date <= datetime.date(2016, 2, 1)
    True
    >>> invoice.click('post')
    >>> invoice.state
    'posted'
    >>> invoice.number is not None
    True

Credit the subscription invoice::

    >>> credit = Wizard('account.invoice.credit', [invoice])
    >>> credit.form.with_refund = True
    >>> credit.form.invoice_date = invoice.invoice_date
    >>> credit.execute('credit')
    >>> invoice.reload()
    >>> invoice.state
    'cancelled'
    >>> credit_notes = Invoice.find([
    ...     ('type', '=', 'out'),
    ...     ('id', '!=', invoice.id),
    ...     ('total_amount', '<', Decimal('0'))])
    >>> credit_note = credit_notes[0]
    >>> credit_note.state
    'paid'
    >>> credit_note.pos == pos
    True

Create a new subscription and verify it inherits POS from configuration::

    >>> subscription2 = Subscription()
    >>> subscription2.party = customer
    >>> subscription2.start_date = datetime.date(2016, 6, 1)
    >>> subscription2.invoice_start_date = datetime.date(2016, 7, 1)
    >>> subscription2.invoice_recurrence = monthly
    >>> line2 = subscription2.lines.new()
    >>> line2.service = service
    >>> line2.quantity = 2
    >>> subscription2.pos == pos
    True

Close the first subscription::

    >>> subscription.click('draft')
    >>> subscription.state
    'draft'
    >>> line, = subscription.lines
    >>> line.end_date = datetime.date(2016, 1, 31)
    >>> subscription.click('quote')
    >>> subscription.click('run')
    >>> subscription.state
    'running'

Generate final consumption and close::

    >>> line_consumption_create = Wizard(
    ...     'sale.subscription.line.consumption.create')
    >>> line_consumption_create.form.date = datetime.date(2016, 2, 1)
    >>> line_consumption_create.execute('create_')

    >>> len(LineConsumption.find([]))
    31

    >>> subscription.reload()
    >>> line, = subscription.lines
    >>> line.next_consumption_date is None
    True
    >>> subscription.state
    'closed'
