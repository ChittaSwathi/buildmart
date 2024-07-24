from odoo import api, fields, models, _
from . import BSnum2words
from odoo.exceptions import UserError
import datetime
from datetime import datetime


class BSPurchaseOrder(models.Model):
    _inherit = "purchase.order"
    _order = 'id desc, priority desc, date_order desc'

    t_and_c = fields.One2many('bs.select.terms.conditions', 'po_id', string="Terms & Conditions")
    delivery_address = fields.Text('Delivery Address')

    is_authorized = fields.Boolean('Verified by Manager', help='Verify Invoice with a digital Signature',
                                   default=False, copy=False)
    authorized_by = fields.Many2one('res.users', 'Verified By', ondelete='restrict', copy=False,
                                    help='Invoice has been Verified with a digital Signature', )
    show_authorize = fields.Boolean(compute='_compute_visibility', string='Show Auth')
    reauthorization_text = fields.Text('Reauthorization Notes')

    def action_authorize_digitally(self):
        ''' Authorize order to send digitally with their Signatory '''
        for po in self.filtered(lambda po: not po.is_authorized):
            if po.user_has_groups('account.group_account_manager') and po.user_has_groups('buildmart.group_account_authorize'):
                if not self.env.user.sign_signature:
                    raise UserError(_('Digital Signatory of yours does not exist, Please contact your Administator !!'))
                else:
                    if po.reauthorization_text:
                        po.write({'reauthorization_text': 'This order has been amended on %s, it supersides any changes done prior to %s.' % (datetime.now().date(), datetime.now().date())})
                    po.write({'is_authorized': True, 'authorized_by': self.env.user.id})
                    po.message_post(body=_("This order has been approved & Verified. "))
            else:
                raise UserError(_(
                    "Sorry!! you don't have necessary permissions to perform this action, Please contact your Administator !!"))

    def button_draft(self):
        res = super(BSPurchaseOrder, self).button_draft()
        # Authorized order cannot be reset by others.
        for po in self.filtered(lambda po: po.is_authorized):
            if not po.user_has_groups('buildmart.group_account_authorize'):
                raise UserError(_('Verified order cannot be reset, Please contact your Manager !!'))
            else:
                po.write({'is_authorized': False, 'authorized_by': False,
                               'reauthorization_text': 'This order has been amended on %s, it supersides any changes done prior to %s.' % (
                                   datetime.now().date(), datetime.now().date())})
        return res

    @api.depends('state', 'is_authorized')
    def _compute_visibility(self):
        for case in self:
            flag = False
            if not case.is_authorized and case.state == 'purchase':
                flag = True
            case.show_authorize = flag

    def get_num2words(self, Amount):
        AmountString = ''
        if Amount:
            AmountString = BSnum2words.num2words("%.2f"%(Amount)) + ' Only'
        return AmountString

    @api.onchange('origin')
    def _onchange_so_ref(self):
        if self.origin:
            SO = self.env['sale.order'].sudo().search([('name','=',self.origin)], limit=1)
            if SO and SO.partner_shipping_id:
                ShipAdd = SO.partner_shipping_id
                DelAdd = ShipAdd.name if not ShipAdd.parent_id else ShipAdd.parent_id.name
                if ShipAdd.street: DelAdd += '\n' + ShipAdd.street
                if ShipAdd.street2: DelAdd += '\n' + ShipAdd.street2
                if ShipAdd.district_id: DelAdd += '\n' + ShipAdd.district_id.name
                if ShipAdd.city: DelAdd += ', '+ShipAdd.city
                if ShipAdd.state_id: DelAdd += '\n' + ShipAdd.state_id.name + ' (' + ShipAdd.state_id.code + ')'
                if ShipAdd.zip: DelAdd += ' - '+ ShipAdd.zip
                self.delivery_address = DelAdd
        else:
            self.delivery_address = ""

    def get_so_del_address(self, Origin):
        return self.env['sale.order'].sudo().search([('name','=',Origin)], limit=1)

    # Overridden
    def button_confirm(self):
        res = super(BSPurchaseOrder, self).button_confirm()
        if self.partner_id.id == self.env.ref('buildmart.bs_demo_vendor').id:
            raise UserError(_("Please assign a vendor, recheck product quantity and price."))
        return res


class BSPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    hsn_code = fields.Char("HSN Code")