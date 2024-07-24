from odoo import api, fields, models
import xml, requests, hashlib, hmac
from odoo.http import request
from odoo.osv import expression


class BSPaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    utr_no = fields.Char('UTR Number', copy=False)
    to_skip = fields.Boolean('Skip', copy=False, help="To Skip if already validated in requery api of atom",
                             default=False)

    #     state = fields.Selection(selection_add=[('failed', 'Failed')])

    # call back method
    def atom_callback(self, data):
        reference, status = data.get('MerchantTxnID'), data.get('VERIFIED')
        tx = self.env['payment.transaction'].search([('reference', '=', reference)])
        if status == 'SUCCESS':
            if tx:
                tx._set_transaction_done()
                return True
        if status == 'FAILED':
            if tx:
                tx._set_transaction_cancel()
                return False
        return False


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    is_neft = fields.Boolean(string='Is NEFT/RTGS ?')
    customer_type = fields.Selection([('b2b', 'B2B'),
                                      ('b2c', 'B2C'),
                                      ('both', 'Both')], string='Customer Type', default="both")

    prod_atom_url = fields.Char(string='Atom Production Url', groups='base.group_user',
                                help="This url will connect to atom production server")
    test_atom_url = fields.Char(string='Atom Test Url', groups='base.group_user',
                                help="This url will connect to atom test server")

    #Overridden
    @api.model
    def _get_compatible_acquirers(
            self, company_id, partner_id, currency_id=None, force_tokenization=False,
            is_validation=False, **kwargs
    ):
        PartnerGroup = request.env.user.partner_id.customer_type
        if PartnerGroup:
            PartnerGroupFilter = [('customer_type', 'in', [PartnerGroup, 'both'])]
        else:
            PartnerGroupFilter = [('customer_type', '=', 'both')]

        # Compute the base domain for compatible acquirers
        domain = ['&', ('state', 'in', ['enabled', 'test']), ('company_id', '=', company_id)]
        domain = expression.AND([domain, PartnerGroupFilter]) #CustomerGroup specific acquirers

        # Handle partner country
        partner = self.env['res.partner'].browse(partner_id)
        if partner.country_id:  # The partner country must either not be set or be supported
            domain = expression.AND([
                domain,
                ['|', ('country_ids', '=', False), ('country_ids', 'in', [partner.country_id.id])]
            ])

        # Handle tokenization support requirements
        if force_tokenization or self._is_tokenization_required(**kwargs):
            domain = expression.AND([domain, [('allow_tokenization', '=', True)]])

        compatible_acquirers = self.env['payment.acquirer'].search(domain)
        return compatible_acquirers


class BSAccountPayment(models.Model):
    _inherit = "account.payment"

    sitename_id = fields.Many2one('bs.sitename', string="Site Name", copy=False)
