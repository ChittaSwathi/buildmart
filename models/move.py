from odoo import models, fields, api, _
import datetime
from datetime import datetime
from odoo.exceptions import UserError
from . import BSnum2words
import json
import base64


class AccountMove(models.Model):
    _inherit = 'account.move'

    arn_id = fields.Many2one('bs.arn', string="ARN Number")
    eway_bill_no = fields.Char("Eway Bill No.")
    vehicle_no = fields.Char("Vehicle No.")
    t_and_c = fields.One2many('bs.select.terms.conditions', 'move_id', string="Terms & Conditions")

    is_authorized = fields.Boolean('Verified by Manager', help='Verify Invoice with a digital Signature',
                                   default=False, copy=False)
    authorized_by = fields.Many2one('res.users', 'Verified By', ondelete='restrict', copy=False,
                                    help='Invoice has been Verified with a digital Signature', )
    show_authorize = fields.Boolean(compute='_compute_visibility', string='Show Auth')
    reauthorization_text = fields.Text('Reauthorization Notes')

    partner_code = fields.Char("Code", related="partner_id.partner_code")
    bs_acct_no = fields.Char("Bank Account", related="partner_id.bs_acct_no")
    ref_date = fields.Date(string='Reference Date', copy=False)
    vat = fields.Char(string='VAT', store=True, copy=False, related='partner_id.vat')
    site_name = fields.Char(string="Site Name", copy=False, related="partner_shipping_id.site_name")
    driver_no = fields.Char("Driver No.", copy=False)
    paid_days_count = fields.Char()
    custom_del_address = fields.Text('Custom Delivery Address', copy=False,
                                     help="Custom Delivery Address")
    sitename_id = fields.Many2one('bs.sitename', string="Site Name", copy=False)
    
    def write(self, vals):
        if 'payment_id' in vals:
            conx = dict(self.env.context)
            if conx.get('active_id', False):
                move = self.env['account.move'].browse(int(conx.get('active_id')))
                invoice_days = move.invoice_date
                today = datetime.today()
                diff =  today.date() - invoice_days
                move.paid_days_count = diff.days
        res = super(AccountMove, self).write(vals)
        return res
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # OVERRIDE
        # Recompute 'partner_shipping_id' based on 'partner_id'.
        res = super(AccountMove, self)._onchange_partner_id()
        domain = {'domain':{'partner_shipping_id':[('id','=',self.partner_id.id)]}}
        addr = self.partner_id.address_get(['delivery'])
        del_addr = self.partner_id.child_ids.filtered(lambda c: c.type == 'delivery') 
        delivery_id = addr and addr.get('delivery')
        self.partner_shipping_id = False
        if del_addr:
            domain = {'domain':{'partner_shipping_id':[('id','=',del_addr.ids)]}}
        if res:
            res['domain'] = domain
            return res
        return domain

    def get_einvoice_values(self):
        attachment_name = '%s_einoivce.json'%(self.name)
        attachment = self.env['ir.attachment'].search([('name', 'ilike', attachment_name),
                                          ('res_model', '=', 'account.move'),
                                          ('res_id', '=', self.id)], limit=1)
        if attachment:
            return json.loads(base64.b64decode(attachment.datas))
        return {}

    def retrieve_attachment(self):
        self.ensure_one()
        AttachmentName = '%s - Tax Invoice.pdf'%(self.name)
        return self.env['ir.attachment'].search([('name', '=',AttachmentName),
                                                ('res_model', '=', 'account.move'),
                                                 ('res_id', '=', self.id)], limit=1)

    def button_draft(self):
        # Authorized Invoice cannot be reset by others.
        for invoice in self.filtered(lambda invoice: invoice.is_authorized):
            if not invoice.user_has_groups('buildmart.group_account_authorize'):
                raise UserError(_('Verified Invoice cannot be reset, Please contact your Accounts Manager !!'))
            else:
                invoice.write({'is_authorized': False, 'authorized_by': False,
                               'reauthorization_text': 'This invoice has been amended on %s, it supersides any raised Invoice prior to %s.' % (
                                   datetime.now().date(), datetime.now().date())})
                attachment = invoice.retrieve_attachment()
                if attachment: attachment.unlink()
        return super(AccountMove, self).button_draft()

    # Overridden: for report name
    def _get_move_display_name(self, show_ref=False):
        self.ensure_one()
        name = ''
        if self.state == 'draft':
            name += {
                'out_invoice': _('Draft Invoice'),
                'out_refund': _('Draft Credit Note'),
                'in_invoice': _('Draft Bill'),
                'in_refund': _('Draft Vendor Credit Note'),
                'out_receipt': _('Draft Sales Receipt'),
                'in_receipt': _('Draft Purchase Receipt'),
                'entry': _('Draft Entry'),
            }[self.move_type]
            name += ' '
        if not self.name or self.name == '/':
            name += '(* %s)' % str(self.id)
        else:
            name += self.name
        ReportName = name + (show_ref and self.ref and ' (%s%s)' % (
        self.ref[:50], '...' if len(self.ref) > 50 else '') or '')

        if self.move_type == 'out_invoice': ReportName += ' - Tax Invoice'
        return ReportName

    #overridden: to get in crores insttead of millions
    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = BSnum2words.num2words("%.2f"%(invoice.amount_total)) + ' Only'

    @api.depends('state', 'is_authorized')
    def _compute_visibility(self):
        for case in self:
            flag = False
            if not case.is_authorized and case.state == 'posted':
                flag = True
            case.show_authorize = flag

    def action_authorize_digitally(self):
        ''' Authorize Invoice to send digitally with their Signatory '''
        for invoice in self.filtered(lambda invoice: not invoice.is_authorized):
            if invoice.user_has_groups('account.group_account_manager') and invoice.user_has_groups('buildmart.group_account_authorize'):
                if not self.env.user.sign_signature:
                    raise UserError(_('Digital Signatory of yours does not exist, Please contact your Administator !!'))
                else:
                    if invoice.reauthorization_text:
                        invoice.write({'reauthorization_text': 'This invoice has been amended on %s, it supersides any raised Invoice prior to %s.' % (datetime.now().date(), datetime.now().date())})
                    invoice.write({'is_authorized': True, 'authorized_by': self.env.user.id})
                    invoice.message_post(body=_("This Invoice has been approved & Verified. "))
            else:
                raise UserError(_(
                    "Sorry!! you don't have necessary permissions to perform this action, Please contact your Administator !!"))

    @api.model
    def create(self, vals):
        AcctMove = super(AccountMove, self).create(vals)
        ctx = self._context
        if ctx.get('active_model') == 'sale.order' and ctx.get('active_id'):
            order = self.env['sale.order'].browse(int(ctx.get('active_id')))
            AcctMove.write({'l10n_in_gst_treatment': order.l10n_in_gst_treatment,
                            'custom_del_address': order.custom_del_address})
            for i in order.t_and_c:
                if i.is_selected:
                    self.env['bs.select.terms.conditions'].create({'move_id': AcctMove.id,
                                                                   'tandc_id': i.tandc_id.id,
                                                                   'category': i.category,
                                                                   'is_selected': i.is_selected})

        if AcctMove.move_type == 'out_invoice':
            for i in AcctMove.invoice_line_ids:
                i.hsn_code = i.product_id.l10n_in_hsn_code
        return AcctMove

    def _get_name_invoice_report(self):
        self.ensure_one()
        return 'buildmart.bs_report_invoice_document'

    def invoice_print(self):
        self.ensure_one()
        if self.authorized_by:
            return self.env.ref('account.account_invoices').report_action(self)
        else:
            raise UserError(_('Invoice needs to be Verified to proceed further.'))

    def invoice_amendend_print(self):
        for invoice in self:
            attachment = invoice.retrieve_attachment()
            print('attachment exists', attachment)
            if attachment:
                print('changing attachment name --', invoice.name + '.pdf')
                attachment.write({'name': invoice.name + '.pdf'})
            message = _("This is an Amendend Invoice Report")
            invoice.message_post(body=message)
        return self.invoice_print()


class BSAccountMoveLine(models.Model):
    _inherit = "account.move.line"

    sitename_id = fields.Many2one('bs.sitename', string="Site Name", copy=False)
    hsn_code = fields.Char("HSN Code")


