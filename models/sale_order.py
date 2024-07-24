from odoo import api, fields, models, _, SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from itertools import groupby
from odoo.addons.stock.models.stock_rule import ProcurementException
from datetime import datetime, timedelta, date
import requests
from odoo.exceptions import UserError, ValidationError


class BSSaleOrder(models.Model):
    _inherit = "sale.order"
    _order = 'id desc, date_order desc'

    # Overridden
    def _default_validity_date(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.use_quotation_validity_days'):
            days = self.env.company.quotation_validity_days
            if days > 0:
                return fields.Datetime.to_string(datetime.now() + timedelta(days))
        return False

    rfq_count = fields.Integer(string="RFQs Count", copy=False, help="No of RFQs raised for this Order",
                               compute='_compute_rfqs_count')
    rfq_id = fields.Many2one('bs.rfq', string="RFQ", help="Holds RFQ whose prices have been accepted and confirmed.")
    wishlist = fields.Boolean(string="Order Wishlisted", copy=False, default=False,
                              help="This field is for check Order wishlisted or not")

    product_tmpl_id = fields.Many2one("product.template", string='Product',
                                      help="Stores product template when raised from website")
    requested_del_date = fields.Date(string="Requested date of delivery")
    reqested_delivery_slot = fields.Selection([('morning', 'Morning'),
                                               ('evening', 'Evening')], string="Delivery Slot", default="morning")
    linked_so_ids = fields.Many2many('sale.order', 'linked_so_rel', 'order_id1', 'order_id2', 'Linked SO',
                                     copy=False)  # todo:remove if not needed

    # Cement Bulk enquiry fields
    is_bulk_enq = fields.Boolean(string="Is bulk enquiry ?")
    enq_project_type = fields.Char(string="Type of Project")
    enq_total_req = fields.Char(string="Total Requirement")
    enq_monthly_req = fields.Char(string="Monthly Requirement")
    enq_current_req = fields.Char(string="Current Requirement")
    enq_approved_brands = fields.Char(string="Approved Brands")
    enq_contact_name = fields.Char(string="Contact Person Name")
    enq_contact_phone = fields.Char(string="Phone Number")
    enq_contact_email = fields.Char(string="Email Address")
    enq_del_address = fields.Char(string="Delivery Address")
    enq_landmark = fields.Char(string="Landmark")
    enq_city = fields.Char(string="City")
    enq_district_id = fields.Many2one("bs.district", string="District")
    enq_state_id = fields.Many2one("res.country.state", string="State")
    enq_pincode = fields.Char(string="Pincode")
    enq_gstin = fields.Char('GSTIN')
    # enq_gstin_id = fields.Many2one("bs.gst", string="GSTIN")
    enq_gst_attachment = fields.Many2one('ir.attachment', string="GSTIN Attachment")
    enq_reg_address = fields.Char(string="Registered Address")

    refund_ticket = fields.Boolean(string="Is Refund Ticket created")

    # Overridden
    validity_date = fields.Datetime(string='Expiration', readonly=True, copy=False,
                                    states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                    default=_default_validity_date)
    # Overridden
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('accept', 'Accepted'),
        ('reject', 'Rejected'),
        ('cancel', 'Cancelled'),
        ('process', 'Processing'),
        ('expire', 'Expired'),
        ('paid', 'Paid')  # expiry date as per vendor as when the order was placed:TODO:remove paid, process
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    rejection_reason = fields.Many2one('bs.rejection.reason', 'Rejection Reason', copy=False)
    rejection_info = fields.Text('Rejection Info.', copy=False)
    show_in_cart = fields.Boolean(string="Show in Cart", copy=False)

    t_and_c = fields.One2many('bs.select.terms.conditions', 'sale_id', string="Terms & Conditions", copy=True)
    logo_attachment = fields.Many2one('ir.attachment', string="Logo attachment")
    logo_tagline = fields.Char(string="Logo Tagline")
    click_upload_id = fields.Many2one('bs.click.upload', 'Click & Upload')
    price_enq_id = fields.Many2one('bs.enquiry', 'Price Enquiry')

    partner_code = fields.Char("Code", related="partner_id.partner_code")
    bs_acct_no = fields.Char("Bank Account", related="partner_id.bs_acct_no")
    client_ref_date = fields.Date('Reference Date', copy=False)

    payment_processed = fields.Boolean('Reference Date', copy=False, help="Was payment tried from frontend?")
    paid = fields.Boolean('Is Order Paid', copy=False, help="When order payment has been successful from frontend.")
    unpaid = fields.Boolean('Is Order Unpaid', copy=False,
                            help="Will be set true if any order's payment is not processed.")
    custom_del_address = fields.Text('Custom Delivery Address', copy=False,
                                     help="Custom Delivery Address")
    
    transport_count = fields.Integer(string="Transport Count", copy=False, help="Shipping Transport Count",
                               compute='_compute_transport_count')
    is_transport = fields.Selection([('yes','Yes'),('no','No')], copy=False, string="Is Transport charge Required ?")
    is_hamali = fields.Selection([('yes','Yes'),('no','No')], copy=False, string="Is Hamali charge Required ?")
    hamali_count = fields.Integer(string="Hamali Count", copy=False, help="Shipping Hamali Count",
                               compute='_compute_hamali_count')

    sitename_id = fields.Many2one('bs.sitename', string="Site Name", copy=False)

    is_authorized = fields.Boolean('Verified by Manager', help='Verify Invoice with a digital Signature',
                                   default=False, copy=False)
    authorized_by = fields.Many2one('res.users', 'Verified By', ondelete='restrict', copy=False,
                                    help='Invoice has been Verified with a digital Signature', )
    show_authorize = fields.Boolean(compute='_compute_visibility', string='Show Auth')
    reauthorization_text = fields.Text('Reauthorization Notes')
    expire_duration = fields.Float(string='Expire Countdown')
    
    @api.model
    def get_timer_time(self, args):
        help_tckt = self.search([('id','=',args)])
        return ['Draft',3000]
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(BSSaleOrder, self).onchange_partner_id()
        domain = {'domain':{'partner_shipping_id':[('id','=',self.partner_id.id)]}}
        addr = self.partner_id.address_get(['delivery'])
        del_addr = self.partner_id.child_ids.filtered(lambda c: c.type == 'delivery') 
        self.partner_shipping_id = False
        if del_addr:
            domain = {'domain':{'partner_shipping_id':[('id','=',del_addr.ids)]}}
        if res:
            res['domain'] = domain
            return res
        return domain

    def action_authorize_digitally(self):
        ''' Authorize sale to send digitally with their Signatory '''
        for sale in self.filtered(lambda sale: not sale.is_authorized):
            if sale.user_has_groups('account.group_account_manager') and sale.user_has_groups('buildmart.group_account_authorize'):
                if not self.env.user.sign_signature:
                    raise UserError(_('Digital Signatory of yours does not exist, Please contact your Administator !!'))
                else:
                    if sale.reauthorization_text:
                        sale.write({'reauthorization_text': 'This order has been amended on %s, it supersides any changes done prior to %s.' % (datetime.now().date(), datetime.now().date())})
                    sale.write({'is_authorized': True, 'authorized_by': self.env.user.id})
                    sale.message_post(body=_("This order has been approved & Verified. "))
                    self.env['bs.notification'].sudo().create({'partner_id': sale.partner_id.id,
                                                           'type': 'order',
                                                           'content': '%s order has been approved & Verified.' % (
                                                               sale.name),
                                                           'url': '/my/orders/%s' % (sale.id)})
            else:
                raise UserError(_(
                    "Sorry!! you don't have necessary permissions to perform this action, Please contact your Administator !!"))

    def action_draft(self):
        res = super(BSSaleOrder, self).action_draft()
        # Authorized sale cannot be reset by others.
        for sale in self.filtered(lambda sale: sale.is_authorized):
            if not sale.user_has_groups('buildmart.group_account_authorize'):
                raise UserError(_('Verified order cannot be reset, Please contact your Manager !!'))
            else:
                sale.write({'is_authorized': False, 'authorized_by': False,
                               'reauthorization_text': 'This order has been amended on %s, it supersides any changes done prior to %s.' % (
                                   datetime.now().date(), datetime.now().date())})
        return res

    @api.depends('state', 'is_authorized')
    def _compute_visibility(self):
        for case in self:
            flag = False
            if not case.is_authorized and case.state == 'sale':
                flag = True
            case.show_authorize = flag

    @api.constrains('is_transport', 'is_hamali')
    def _check_transport_hamali_settings(self):
        """ User must select either yes or no """
        for rec in self:
            if not rec.is_hamali :
                raise ValidationError(_("Please check if hamali charges needs to be applied or not."))
            if not rec.is_transport :
                raise ValidationError(_("Please check if transport charges needs to be applied or not."))


    def sms_notify_price_update(self):
        # BS - generate notifications
        try:
            for rec in self:
                MobVal = rec.partner_id.mobile
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/my/orders/' + str(rec.id)
                Message = """Your price enquiry (%s) is now updated with price. Click here %s for information or call us at %s""" % (
                    rec.name, url, rec.company_id.cust_care_phone)
                sms_provider = self.env['sms.provider'].search([('active_provider','=',True)], limit=1)
                if sms_provider.name == 'VI':
                    url = "https://cts.myvi.in:8443//ManageSms/api/sms/Createsms/json/apikey=%s" % (
                        rec.company_id.sms_apikey)
                    headers = {'Authorization': 'Bearer %s' % (sms_provider.get_sms_token())}
                    params = {
                        "msisdn": MobVal,
                        "sms": Message,
                        "unicode": "0",
                        "senderid": sms_provider.sms_senderid,
                        "pingbackurl": "https://buildmart.com/pingback/sms"
                    }
                    Response = requests.post(url, params, headers=headers)
                if sms_provider.name == 'webking':
                    url = "%s?username=%s&pass=%s&senderid=%s&message=%s&dest_mobileno=%s&msgtype=TXT&response=Y" % (
                        sms_provider.access_point,sms_provider.sms_username,sms_provider.sms_password,sms_provider.sms_senderid,Message,MobVal)
                    Response = requests.post(url)
                self.env['bs.sms.log'].sudo().create({'res_id': rec.partner_id.id, 'model': 'sale.order',
                                                      'sms_type': 'otp', 'subtype': 'others', 'body': Message,
                                                      'sent_time': datetime.now(),
                                                      'recipient_id': rec.partner_id.id,
                                                      'email': rec.partner_id.email, 'mobile': MobVal,
                                                      'response': Response})

                self.env['bs.notification'].sudo().create({'partner_id': rec.partner_id.id,
                                                           'type': 'order',
                                                           'content': 'Your Order %s has been confirmed with prices.' % (
                                                               rec.name),
                                                           'url': '/my/orders/%s' % (rec.id)})
        except Exception as e:
            print('Exception occurred', e)

    # Overridden
    def _prepare_invoice(self):
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
            self.company_id.name, self.company_id.id))

        invoice_vals = {
            'ref': self.client_order_ref or '',
            'ref_date': self.client_ref_date,
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'invoice_user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(
                self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'sitename_id': self.sitename_id.id,
        }
        return invoice_vals

    def action_confirm(self):
        res = super(BSSaleOrder, self).action_confirm()
        # BS - Creating a same SOL valued purchase order for incoming shipments
        for rec in self:
            LineDetails = []
            for line in rec.order_line:
                TaxIDs = []
                for i in line.tax_id:
                    TaxAcct = self.env['account.tax'].search([('name','=',i.name),('type_tax_use','=','purchase')])
                    if TaxAcct: TaxIDs += [TaxAcct.id]
                if self.env.ref('stock_dropshipping.route_drop_shipping').id not in line.product_id.route_ids.ids:
                    LineDetails += [(0, 0, {'product_id': line.product_id.id,
                                            'name': line.product_id.display_name,
                                            'hsn_code': line.product_id.l10n_in_hsn_code,
                                            'product_qty': line.product_uom_qty,
                                            'product_uom': line.product_uom.id,
                                            'taxes_id': TaxIDs,
                                            'sale_order_id': rec.id,
                                            'sale_line_id': line.id})]
            if LineDetails:
                PoVals = {'partner_id': self.env.ref('buildmart.bs_demo_vendor').id,
                          'origin': rec.name,
                          'order_line': LineDetails}
                self.env['purchase.order'].sudo().create(PoVals)  # TODO: bring logged user name
        return res

    # Overridden
    @api.depends('state', 'order_line.invoice_status')
    def _get_invoice_status(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.
        """
        unconfirmed_orders = self.filtered(lambda so: so.state not in ['sale', 'done', 'accept'])
        unconfirmed_orders.invoice_status = 'no'
        confirmed_orders = self - unconfirmed_orders
        if not confirmed_orders:
            return
        line_invoice_status_all = [
            (d['order_id'][0], d['invoice_status'])
            for d in self.env['sale.order.line'].read_group([
                ('order_id', 'in', confirmed_orders.ids),
                ('is_downpayment', '=', False),
                ('display_type', '=', False),
            ],
                ['order_id', 'invoice_status'],
                ['order_id', 'invoice_status'], lazy=False)]
        for order in confirmed_orders:
            line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]
            if order.state not in ('sale', 'done', 'accept'):
                order.invoice_status = 'no'
            elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                order.invoice_status = 'to invoice'
            elif line_invoice_status and all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                order.invoice_status = 'invoiced'
            elif line_invoice_status and all(
                    invoice_status in ('invoiced', 'upselling') for invoice_status in line_invoice_status):
                order.invoice_status = 'upselling'
            else:
                order.invoice_status = 'no'

    def get_order_product(self):
        product = self.order_line.mapped('product_id').filtered(lambda x: x.type != 'service').mapped('product_tmpl_id')
        if not product:
            product = self.order_line.mapped('product_id').mapped('product_tmpl_id')
        if product: product = product[0]
        return product

    def get_order_product_attrbute(self):
        BrandAttrID = self.env.ref('buildmart.brand_attribute').id
        attr = ', '.join(self.order_line.mapped('product_id').product_template_attribute_value_ids.filtered(
            lambda x: x.attribute_id.id != BrandAttrID).mapped('name'))
        return attr

    def get_order_qty(self):
        qty = 0
        lines = self.order_line.filtered(lambda x: x.product_id.type != 'service')
        if lines:
            qty = sum(lines.mapped('product_uom_qty'))
        return qty

    def write(self, vals):
        res = super(BSSaleOrder, self).write(vals)
        if vals.get('state') and vals.get('state') == 'sent':
            self.sms_notify_price_update()
        return res

    # Overridden
    def action_done(self):
        for order in self:
            tx = order.sudo().transaction_ids.get_last_transaction()
            if tx and tx.state == 'pending' and tx.acquirer_id.provider == 'transfer':
                tx._set_transaction_done()
                tx.write({'is_processed': True})
        if self._context.get('bs_vendor_info', False):
            return self.write({'state': 'state'})
        else:
            return self.write({'state': 'done'})

    def _compute_rfqs_count(self):
        for so in self:
            so.rfq_count = self.env['bs.rfq'].search_count([('so_id', '=', so.id)])
            
    def _compute_transport_count(self):
        for order in self:
            for inv in order.invoice_ids:
                uoms = inv.invoice_line_ids.filtered(lambda x: x.product_id.detailed_type != 'service').mapped('product_uom_id.id')
                for uom in uoms:
                    trasport = self.env['order.transport'].search([('invoice_id','=',inv.id),('order_id','=',order.id),('product_uom_id','=',uom)])
                    if not trasport:
                        qty = sum(inv.invoice_line_ids.filtered(lambda x: x.product_uom_id.id == uom and x.product_id.detailed_type != 'service').mapped('quantity'))
                        self.env['order.transport'].create({'order_id':order.id,'invoice_id':inv.id,'quantity':qty,'product_uom_id':uom})
            order.transport_count = len(order.invoice_ids) if order.invoice_ids else 0
            
    def _compute_hamali_count(self):
        for order in self:
            for inv in order.invoice_ids:
                uoms = inv.invoice_line_ids.filtered(lambda x: x.product_id.detailed_type != 'service').mapped('product_uom_id.id')
                for uom in uoms:
                    trasport = self.env['order.hamali'].search([('invoice_id','=',inv.id),('order_id','=',order.id),('product_uom_id','=',uom)])
                    if not trasport:
                        qty = sum(inv.invoice_line_ids.filtered(lambda x: x.product_uom_id.id == uom and x.product_id.detailed_type != 'service').mapped('quantity'))
                        self.env['order.hamali'].create({'order_id':order.id,'invoice_id':inv.id,'quantity':qty,'product_uom_id':uom})
            order.hamali_count = len(order.invoice_ids) if order.invoice_ids else 0
        
        

    def action_view_rfq(self):
        self.ensure_one()
        action = self.env.ref('buildmart.rfq_action').read()[0]
        RFQs = self.env['bs.rfq'].search([('so_id', '=', self.id)])
        action['domain'] = [('id', 'in', RFQs.ids)]
        if len(RFQs) == 1:
            action['views'] = [(self.env.ref('buildmart.rfq_form_view').id, 'form')]
            action['res_id'] = RFQs.id
        return action
    
    def action_view_transport(self):
        self.ensure_one()
        action = self.env.ref('buildmart.transport_action').read()[0]
        orders = self.env['order.transport'].search([('order_id', '=', self.id)])
        action['domain'] = [('id', 'in', orders.ids)]
        action['views'] = [(self.env.ref('buildmart.transport_tree_view').id, 'tree')]
        return action
    
    def action_view_hamali(self):
        self.ensure_one()
        action = self.env.ref('buildmart.hamali_action').read()[0]
        orders = self.env['order.hamali'].search([('order_id', '=', self.id)])
        action['domain'] = [('id', 'in', orders.ids)]
        action['views'] = [(self.env.ref('buildmart.hamali_tree_view').id, 'tree')]
        return action

    @api.model
    def customer_cart(self, user):
        partner_id = user.partner_id.id
        quotations = self.env['sale.order'].search([('partner_id', '=', partner_id)]). \
            filtered(lambda x: x.show_in_cart and x.state == 'sale' and not x.payment_processed)
        amount_total = sum(quotations.mapped('amount_total'))
        sub_total = sum(quotations.mapped('amount_untaxed'))
        amount_tax = sum(quotations.mapped('amount_tax'))
        order_details = {
            'quotations': quotations,
            'amount_total': amount_total,
            'sub_total': sub_total,
            'amount_tax': amount_tax
        }
        return order_details

    @api.model
    def checkout_orders(self, order_ids):
        order_ids = [int(i) for i in order_ids]
        quotations = self.env['sale.order'].browse(order_ids)
        cs = quotations[0].company_id.currency_id.symbol
        html = ''
        for quotation in quotations:
            quot_amount = cs + "{:,.2f}".format(quotation.amount_total)
            html += """<tr><td class="font-family-bold font-size-14 text-color-block border-left-table">
                        <p class="pad-mar-0 mar-bot-5">Order Number</p>
                        <p class="pad-mar-0 font-size-14 font-color-gray-7">Total Amount</p>
                      </td>
                      <td class="font-family-bold font-size-14 text-color-block border-right-table">
                        <p class="text-right pad-mar-0 mar-bot-5">""" + quotation.name + """</p>
                        <p class="text-right pad-mar-0 font-size-14 font-color-gray-7">""" + str(quot_amount) + """</p>
                      </td></tr>"""

        amount_total = cs + "{:,.2f}".format(sum(quotations.mapped('amount_total')))
        sub_total = sum(quotations.mapped('amount_untaxed'))
        amount_tax = sum(quotations.mapped('amount_tax'))
        html += """<tr class="total-amount">
                      <td class="font-family-bold font-size-14 text-color-block border-left-table">
                        <p class="pad-mar-0 font-size-16 text-color-block">All Orders Total Amount</p>
                      </td>
                      <td class="font-family-bold font-size-14 text-color-block border-right-table">
                        <p class="text-right pad-mar-0 font-size-16 text-color-block"><span id="chk_total">""" + str(
            amount_total) + """</span></p>
                      </td>
                    </tr>"""

        order_details = {
            'order_details': html
        }
        return order_details

    @api.model
    def cancel_open_order(self, order):
        order = self.env['sale.order'].sudo().browse(int(order.get('order_id')))
        order.update({'state': 'cancel'})
        return True

    @api.model
    def remove_from_cart(self, order_id):
        quotation = self.env['sale.order'].browse(int(order_id))
        quotation.state = 'cancel'
        return True

    @api.model
    def orders_payment(self, order_ids):
        orderIds = [int(x) for x in order_ids.split(',')]
        quotations = self.env['sale.order'].browse(orderIds)
        amount_total = sum(quotations.mapped('amount_total'))
        sub_total = sum(quotations.mapped('amount_untaxed'))
        amount_tax = sum(quotations.mapped('amount_tax'))
        return {'orders': quotations, 'amount_total': amount_total, 'sub_total': sub_total, 'amount_tax': amount_tax}

    def raise_rfqs(self):  # TODO: make popup with selectable values
        ''' Raises RFQs to mapped vendors of a product '''
        for rec in self:
            if not self.env['bs.rfq'].search([('so_id', '=', rec.id)]):
                OrderLines = []
                for line in rec.order_line:
                    OrderLines += [(0, 0, {'product_id': line.product_id.id,
                                           'name': line.name,
                                           'product_qty': line.product_uom_qty,
                                           'taxes_id': line.tax_id.ids,
                                           'product_uom': line.product_uom.id})]
                if OrderLines:
                    VendorInfo = []
                    for product in rec.order_line.filtered(
                            lambda x: x.product_id not in [self.env.ref('buildmart.hamali_charges').id,
                                                           self.env.ref('buildmart.transport_charges').id]).mapped(
                        'product_id.product_tmpl_id'):

                        Sellers = product.seller_ids if not product.attribute_line_ids else product.variant_seller_ids
                        if Sellers:
                            for i in Sellers[:5]:
                                VendorInfo += [
                                    {'so_id': rec.id, 'vendor_id': i.name.id, 'partner_id': rec.partner_id.id,
                                     'order_line': OrderLines, 'origin': rec.name, 'supplier_info_id': i.id}]
                        else:
                            raise UserError(_("No Vendors Found!!"))
                    self.env['bs.rfq'].create(VendorInfo)

class BSSaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    hsn_code = fields.Char("HSN Code")

    @api.onchange('product_id')
    def _onchange_discount(self):
        super(BSSaleOrderLine, self)._onchange_discount()
        self.hsn_code = self.product_id.l10n_in_hsn_code


class TransportDetails(models.Model):
    _name = 'order.transport'
    
    order_id = fields.Many2one("sale.order", string='Order')
    partner_id = fields.Many2one("res.partner", related="order_id.partner_id", string='Customer', store=True)
    invoice_id = fields.Many2one("account.move", string='Invoice')
    vehicle_no = fields.Char(related="invoice_id.vehicle_no", string="Vehicle No.")
    site_name = fields.Char(string="Site Name", copy=False, related="invoice_id.site_name")
    sitename_id = fields.Many2one('bs.sitename', string="Site Name", copy=False)
    driver_no = fields.Char(related="invoice_id.driver_no", string="Driver No.", copy=False)
    amount_total = fields.Monetary(string='Total', default=0.0)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company.id)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', ondelete="restrict")
    transporter_name = fields.Char(string="Transport Name")
    partner_transporter = fields.Many2one("res.partner", string='Transport Name')
    bill_no = fields.Char(string="Bill No.")
    user_id = fields.Many2one("res.users", string='Approver')
    approved_date = fields.Date(string='Approver Date')
    state = fields.Selection([
        ('draft', 'Un Paid'),
        ('post', 'Paid')
    ], string='Status', readonly=True, copy=False, index=True, default='draft')
    
    def update_transport(self):
        self.state = 'post'
        self.user_id = self.env.user.id
        self.approved_date = date.today().strftime('%Y-%m-%d')
        
        
class HamaliDetails(models.Model):
    _name = 'order.hamali'
    
    order_id = fields.Many2one("sale.order", string='Order')
    partner_id = fields.Many2one("res.partner", related="order_id.partner_id", string='Customer', store=True)
    invoice_id = fields.Many2one("account.move", string='Invoice')
    vehicle_no = fields.Char(related="invoice_id.vehicle_no", string="Vehicle No.")
    site_name = fields.Char(string="Site Name", copy=False, related="invoice_id.site_name")
    sitename_id = fields.Many2one('bs.sitename', string="Site Name", copy=False)
    driver_no = fields.Char(related="invoice_id.driver_no", string="Driver No.", copy=False)
    amount_total = fields.Monetary(string='Total', default=0.0)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company.id)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', ondelete="restrict")
    transporter_name = fields.Char(string="Transport Name")
    partner_transporter = fields.Many2one("res.partner", string='Transport Name')
    bill_no = fields.Char(string="Bill No.")
    user_id = fields.Many2one("res.users", string='Approver')
    approved_date = fields.Date(string='Approver Date')
    state = fields.Selection([
        ('draft', 'Un Paid'),
        ('post', 'Paid')
    ], string='Status', readonly=True, copy=False, index=True, default='draft')
    
    def update_hamali(self):
        self.state = 'post'
        self.user_id = self.env.user.id
        self.approved_date = date.today().strftime('%Y-%m-%d')


class customerWishlist(models.Model):
    _name = 'customer.wishlist'

    product_tmpl_id = fields.Many2one("product.template", string='Product',
                                      help="Stores product template when raised from website")
    state = fields.Selection([('open', 'Open'),
                              ('close', 'Close')], string='Customer Type', default="open")
    partner_id = fields.Many2one("res.partner", string='Customer')
    order_id = fields.Many2one("sale.order", string='Order')

    @api.model
    def add_remove_Wishlist(self, option):
        print('add_remove_Wishlist', option)
        partner_id = self.env.user.partner_id.id
        product_templ_id = option.get('product_templ_id')
        order_name = option.get('so_name')
        order = self.env['sale.order'].sudo().search([('name', '=', order_name)])

        domain = [('product_tmpl_id', '=', product_templ_id),
                  ('partner_id', '=', partner_id),
                  ('state', '=', 'open')]
        if order:
            domain += [('order_id', '=', order.id)]
        else:
            domain += [('order_id', '=', False)]
        check_list = self.env['customer.wishlist'].sudo().search(domain)
        if check_list:
            print('check_list if')
            check_list.sudo().state = 'close'
            return False
        if not check_list:
            print('check_list else')
            vals = {'partner_id': partner_id, 'product_tmpl_id': product_templ_id, 'state': 'open'}
            if order:
                vals.update({'order_id': order.id})
            self.env['customer.wishlist'].sudo().create(vals)
            return True

    @api.model
    def remove_Wishlist(self, option):
        wish_id = option.get('order_id')
        check_list = self.env['customer.wishlist'].sudo().browse(int(wish_id))
        if check_list:
            check_list.sudo().state = 'close'
        return True

    @api.model
    def add_to_cart(self, option):
        rfq_id = option.get('order_id')
        check_list = self.env['sale.order'].sudo().browse(int(rfq_id))
        if check_list:
            check_list.show_in_cart = True
        wish_id = option.get('wish_id')
        wishLst = self.env['customer.wishlist'].sudo().browse(int(wish_id))
        if wishLst:
            wishLst.sudo().state = 'close'
        return True


class BSStockPicking(models.Model):
    _inherit = "stock.picking"

    status_date_details = fields.Char('Status Update')
    bs_pick_status = fields.Selection([('Order Placed','Order Placed'),('Packed','Packed'),('Dispatched','Dispatched'),('Out for Delivery','Out for Delivery'),('Delivered','Delivered')], string="Status", default="Order Placed")
    delivery_person = fields.Many2one(
        'res.users', 'Delivery Person', tracking=True,
        domain=[('user_type', '=', 'dp')],
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        default=lambda self: self.env.user)

    is_authorized = fields.Boolean('Verified by Manager', help='Verify Invoice with a digital Signature',
                                   default=False, copy=False)
    authorized_by = fields.Many2one('res.users', 'Verified By', ondelete='restrict', copy=False,
                                    help='Invoice has been Verified with a digital Signature', )
    show_authorize = fields.Boolean(compute='_compute_visibility', string='Show Auth')
    reauthorization_text = fields.Text('Reauthorization Notes')

    def action_authorize_digitally(self):
        ''' Authorize order to send digitally with their Signatory '''
        for po in self.filtered(lambda po: not po.is_authorized):
            if po.user_has_groups('account.group_account_manager') and po.user_has_groups(
                    'buildmart.group_account_authorize'):
                if not self.env.user.sign_signature:
                    raise UserError(_('Digital Signatory of yours does not exist, Please contact your Administator !!'))
                else:
                    if po.reauthorization_text:
                        po.write({'reauthorization_text': 'This order has been amended on %s, it supersides any changes done prior to %s.' % (
                                     datetime.now().date(), datetime.now().date())})
                    po.write({'is_authorized': True, 'authorized_by': self.env.user.id})
                    po.message_post(body=_("This order has been approved & Verified. "))
            else:
                raise UserError(_(
                    "Sorry!! you don't have necessary permissions to perform this action, Please contact your Administator !!"))

    @api.depends('state', 'is_authorized')
    def _compute_visibility(self):
        for case in self:
            flag = False
            if not case.is_authorized and case.state == 'done':
                flag = True
            case.show_authorize = flag

    def create(self, vals):
        vals['status_date_details'] = 'Order Placed' +'___' + str(datetime.now())
        res = super(BSStockPicking, self).create(vals)
        return res

    def write(self, vals):
        if 'bs_pick_status' in vals:
            vals['status_date_details'] = self.status_date_details + '___' + vals['bs_pick_status'] + '___' + str(datetime.now())
        res = super(BSStockPicking, self).write(vals)
        return res


class BSStockRule(models.Model):
    _inherit = 'stock.rule'

    # Overridden
    @api.model
    def _run_buy(self, procurements):
        ctx = self._context
        BsVendorInfo = ctx.get('bs_vendor_info', {})

        procurements_by_po_domain = defaultdict(list)
        errors = []
        # Origins we don't want to appear in the PO source field.
        origins_to_hide = [
            _('Manual Replenishment'),
            _('Replenishment Report'),
        ]
        for procurement, rule in procurements:

            # Get the schedule date in order to find a valid seller
            procurement_date_planned = fields.Datetime.from_string(procurement.values['date_planned'])
            schedule_date = (procurement_date_planned - relativedelta(days=procurement.company_id.po_lead))

            if not BsVendorInfo:
                supplier = False
                if procurement.values.get('supplierinfo_id'):
                    supplier = procurement.values['supplierinfo_id']
                else:
                    supplier = procurement.product_id.with_company(procurement.company_id.id)._select_seller(
                        partner_id=procurement.values.get("supplierinfo_name"),
                        quantity=procurement.product_qty,
                        date=schedule_date.date(),
                        uom_id=procurement.product_uom)
            else:
                supplier = BsVendorInfo.get('supplier_info_id')

            # Fall back on a supplier for which no price may be defined. Not ideal, but better than
            # blocking the user.
            supplier = supplier or procurement.product_id._prepare_sellers(False).filtered(
                lambda s: not s.company_id or s.company_id == procurement.company_id
            )[:1]

            if not supplier:
                msg = _(
                    'There is no matching vendor price to generate the purchase order for product %s (no vendor defined, minimum quantity not reached, dates not valid, ...). Go on the product form and complete the list of vendors.') % (
                          procurement.product_id.display_name)
                errors.append((procurement, msg))

            partner = supplier.name
            # we put `supplier_info` in values for extensibility purposes
            procurement.values['supplier'] = supplier
            procurement.values['propagate_cancel'] = rule.propagate_cancel

            domain = rule._make_po_get_domain(procurement.company_id, procurement.values, partner)
            procurements_by_po_domain[domain].append((procurement, rule))

        if errors:
            raise ProcurementException(errors)

        for domain, procurements_rules in procurements_by_po_domain.items():
            # Get the procurements for the current domain.
            # Get the rules for the current domain. Their only use is to create
            # the PO if it does not exist.
            procurements, rules = zip(*procurements_rules)

            # Get the set of procurement origin for the current domain.
            origins = set([p.origin for p in procurements if p.origin not in origins_to_hide])
            # Check if a PO exists for the current domain.
            po = self.env['purchase.order'].sudo().search([dom for dom in domain], limit=1)
            company_id = procurements[0].company_id
            if not po:
                # We need a rule to generate the PO. However the rule generated
                # the same domain for PO and the _prepare_purchase_order method
                # should only uses the common rules's fields.
                vals = rules[0]._prepare_purchase_order(company_id, origins, [p.values for p in procurements])
                # The company_id is the same for all procurements since
                # _make_po_get_domain add the company in the domain.
                # We use SUPERUSER_ID since we don't want the current user to be follower of the PO.
                # Indeed, the current user may be a user without access to Purchase, or even be a portal user.
                po = self.env['purchase.order'].with_company(company_id).with_user(SUPERUSER_ID).create(vals)
            else:
                # If a purchase order is found, adapt its `origin` field.
                if po.origin:
                    missing_origins = origins - set(po.origin.split(', '))
                    if missing_origins:
                        po.write({'origin': po.origin + ', ' + ', '.join(missing_origins)})
                else:
                    po.write({'origin': ', '.join(origins)})

            procurements_to_merge = self._get_procurements_to_merge(procurements)
            procurements = self._merge_procurements(procurements_to_merge)

            po_lines_by_product = {}
            grouped_po_lines = groupby(
                po.order_line.filtered(lambda l: not l.display_type and l.product_uom == l.product_id.uom_po_id).sorted(
                    lambda l: l.product_id.id), key=lambda l: l.product_id.id)
            for product, po_lines in grouped_po_lines:
                po_lines_by_product[product] = self.env['purchase.order.line'].concat(*list(po_lines))
            po_line_values = []
            for procurement in procurements:
                po_lines = po_lines_by_product.get(procurement.product_id.id, self.env['purchase.order.line'])
                po_line = po_lines._find_candidate(*procurement)

                if po_line:
                    # If the procurement can be merge in an existing line. Directly
                    # write the new values on it.
                    vals = self._update_purchase_order_line(procurement.product_id,
                                                            procurement.product_qty, procurement.product_uom,
                                                            company_id,
                                                            procurement.values, po_line)
                    po_line.write(vals)
                else:
                    # If it does not exist a PO line for current procurement.
                    # Generate the create values for it and add it to a list in
                    # order to create it in batch.
                    partner = procurement.values['supplier'].name
                    po_line_values.append(self.env['purchase.order.line']._prepare_purchase_order_line_from_procurement(
                        procurement.product_id, procurement.product_qty,
                        procurement.product_uom, procurement.company_id,
                        procurement.values, po))
            if BsVendorInfo:
                for i in po_line_values: i.update({'price_unit': BsVendorInfo[i['product_id']].get('price_unit', 0)})

            self.env['purchase.order.line'].sudo().create(po_line_values)