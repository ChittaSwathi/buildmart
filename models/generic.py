from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.http import request
import datetime
from datetime import datetime
import random

class BSView(models.Model):
    _inherit = 'ir.ui.view'

    def check_user_group(self):
        # x = request.website.is_publisher()
        if request.env.user and request.session.uid and (not request.env.user.has_group('base.group_portal')):
            return True
        return False

    # Overridden: For Header & Footer
    @api.model
    def _prepare_qcontext(self):
        """ Returns the qcontext : rendering context with website specific value (required
            to render website layout template)
        """
        qcontext = super(BSView, self)._prepare_qcontext()
        if request and getattr(request, 'is_frontend', False):
            Website = self.env['website']
            editable = request.website.is_publisher()
            translatable = editable and self._context.get('lang') != request.env['ir.http']._get_default_lang().code
            editable = not translatable and editable

            cur = Website.get_current_website()
            if self.env.user.has_group('website.group_website_publisher') and self.env.user.has_group(
                    'website.group_multi_website'):
                qcontext['multi_website_websites_current'] = {'website_id': cur.id, 'name': cur.name,
                                                              'domain': cur._get_http_domain()}
                qcontext['multi_website_websites'] = [
                    {'website_id': website.id, 'name': website.name, 'domain': website._get_http_domain()}
                    for website in Website.search([]) if website != cur
                ]

                cur_company = self.env.company
                qcontext['multi_website_companies_current'] = {'company_id': cur_company.id, 'name': cur_company.name}
                qcontext['multi_website_companies'] = [
                    {'company_id': comp.id, 'name': comp.name}
                    for comp in self.env.user.company_ids if comp != cur_company
                ]
            Partner = self.env.user.partner_id
            homepageRec = self.env['bs.homepage'].sudo().search([('company_id', '=', self.env.company.id)], limit=1)
            FooterLinks = homepageRec.footer_link_ids if homepageRec else False
            HeaderSearchData = homepageRec.header_search_ids if homepageRec else False

            eCommCategs = self.env['product.public.category'].search([('parent_id', '=', False),
                                                                      ('customer_type', 'in',
                                                                       [Partner.customer_type, 'both'])])
            ShippingIds = {'default': {}, 'others': {}}
            if Partner.default_shipping_id:
                ShippingIds.update(
                    {'default': {Partner.default_shipping_id.id: str(Partner.default_shipping_id.city) + ' - ' + str(
                        Partner.default_shipping_id.zip)}})
            elif Partner.city or Partner.zip:
                ShippingIds.update({'default': {Partner.id: str(Partner.city) + ' - ' + str(Partner.zip)}})

            if Partner.child_ids.filtered(lambda x: x.type == 'delivery'):
                OtherAddress = {Partner.id: str(Partner.city) + ' - ' + str(Partner.zip)}
                for i in Partner.child_ids.filtered(lambda x: x.type == 'delivery'):
                    OtherAddress.update({i.id: str(i.city) + ' - ' + str(i.zip)})
                ShippingIds.update(others=OtherAddress)

            NotificationsCount = self.env['bs.notification'].sudo().search_count([('partner_id', '=', Partner.id),
                                                                                  ('read', '=', False)])
            Notifications = self.env['bs.notification'].sudo().search([('partner_id', '=', Partner.id),('read','=',False)],
                                                                      order="id desc")
            promotion = random.choice(self.env['bs.generic.promotion'].sudo().search([])) \
                if self.env['bs.generic.promotion'].sudo().search([]) else False
            qcontext.update(dict(
                brands=self.env['product.attribute.value'].sudo().search(
                    [('attribute_id', '=', self.env.ref('buildmart.brand_attribute').id)]),
                main_object=self,
                website=request.website,
                is_view_active=request.website.is_view_active,
                res_company=request.website.company_id.sudo(),
                translatable=translatable,
                editable=editable,

                footer_links=FooterLinks,
                mega_menu=eCommCategs.filtered(lambda x: x.megamenu).sorted(lambda x: x.megamenu_sequence),
                mega_brands=self.get_all_brands(),
                header_search=HeaderSearchData,
                shipping_ids=ShippingIds,
                total_orders=self.env['sale.order'].sudo().search_count(
                    [('partner_id', '=', request.env.user.partner_id.id),
                     ('state', '=', 'sale'), ('show_in_cart', '=', True),('payment_processed','=',False)]) or 0,
                customer_type=Partner.customer_type if Partner else False,
                customer=Partner if Partner else False,
                gstin=(Partner.vat if not Partner.parent_id else Partner.parent_id.vat) if Partner else '',
                default_shipping_id=Partner.default_shipping_id if Partner.default_shipping_id else Partner,
                so_reject_reasons=request.env['bs.rejection.reason'].sudo().search([]),
                BrandAttrID=request.env.ref('buildmart.brand_attribute').id,
                notifications_count=NotificationsCount,
                notifications=Notifications,
                promotion = promotion,
            ))
        return qcontext

    def get_all_brands(self):
        """ Fetches all brands from ecommerce categories (including sub categories) """
        AllBrands = {}
        Partner = self.env.user.partner_id
        eCommObj = self.env['product.public.category']

        for eCatag in eCommObj.search([('customer_type', 'in', [Partner.customer_type, 'both'])]):
            ProductIDs = self.env['product.template'].search(['|', ('public_categ_ids', 'child_of', int(eCatag.id)),
                                                              ('public_categ_ids', '=', int(eCatag.id))]).ids
            Brands = self.env['product.template.attribute.line'].search(
                [('attribute_id', '=', self.env.ref('buildmart.brand_attribute').id),
                 ('product_tmpl_id', 'in', ProductIDs)]).mapped('value_ids').filtered(lambda x: x.is_top_brand == True)
            AllBrands[eCatag] = Brands
        return AllBrands


class BSNotifications(models.Model):
    _name = 'bs.notification'

    name = fields.Char('Ref#')
    partner_id = fields.Many2one('res.partner', 'Partner')
    content = fields.Text('Notification Content')
    url = fields.Char('Redirecting URL')
    type = fields.Selection([('generic', 'Generic'),
                             ('product', 'Product'),
                             ('order','Order')], string='Notification Type',help="For frontend image control")
    read = fields.Boolean('Was Read?', default=False)
    read_time = fields.Datetime('Notification Read Time')

    @api.model
    def create(self, vals):
        Notification = super(BSNotifications, self).create(vals)
        Notification.name = self.env['ir.sequence'].next_by_code('bs.notification.code')
        return Notification

    def write(self, vals):
        res = super(BSNotifications, self).write(vals)
        if not self.name: self.env['ir.sequence'].next_by_code('bs.notification.code')
        return res


class BSServiceability(models.Model):
    _name = "bs.pincode.serviceability"
    _order = 'pincode desc'

    city = fields.Char('City')
    state_id = fields.Many2one('res.country.state', 'State')
    district_id = fields.Many2one('bs.district', 'District')
    pincode = fields.Char('Pincode')
    is_serviceable = fields.Boolean('Is Serviceable', default=False)


class BSTermsConditions(models.Model):
    _name = "bs.terms.conditions"

    category = fields.Selection([('steel', 'Steel'),
                                 ('cement', 'Cement'),
                                 ('paints', 'Paints'),
                                 ('blocks', 'Blocks'),
                                 ('rmc', 'RMC'),
                                 ('safety', 'Safety Products'),
                                 ('bricks', 'Bricks')], string="Category")
    name = fields.Text(string="Terms")
    active = fields.Boolean(string='active', default=True)
    display_model = fields.Selection([('so', 'SO'),
                                      ('po', 'PO'),
                                      ('inv', 'INV')], string="Display Model")

class BSSelectTandC(models.Model):
    _name = "bs.select.terms.conditions"

    sequence = fields.Integer('Sequence', help="Sequence used to order T&C for report")
    is_selected = fields.Boolean(string="Select", default=True)
    tandc_id = fields.Many2one("bs.terms.conditions", 'Terms')
    sale_id = fields.Many2one('sale.order')
    move_id = fields.Many2one('account.move')
    po_id = fields.Many2one('purchase.order')
    category = fields.Selection([('steel', 'Steel'),
                                 ('cement', 'Cement'),
                                 ('paints', 'Paints'),
                                 ('blocks', 'Blocks'),
                                 ('rmc', 'RMC'),
                                 ('safety', 'Safety Products'),
                                 ('bricks', 'Bricks')], string="Category") #Ensure as per bs.terms.conditions category

    @api.onchange('category')
    def _onchange_category(self):
        if self.category:
            return {'domain':{'tandc_id':[('category','=',self.category)]}}


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    upload_enquiry_id = fields.Many2one('bs.enquiry')


class BSSORejectionReason(models.Model):
    _name = "bs.rejection.reason"

    name = fields.Char(string="Reason")


class BSARNumber(models.Model):
    _name = 'bs.arn'

    month = fields.Selection([('1', 'January'),
                              ('2', 'February'),
                              ('3', 'March'),
                              ('4', 'April'),
                              ('5', 'May'),
                              ('6', 'June'),
                              ('7', 'July'),
                              ('8', 'August'),
                              ('9', 'September'),
                              ('10', 'October'),
                              ('11', 'November'),
                              ('12', 'December')], string="Month")
    year = fields.Char(default=datetime.now().year, string="Year")
    arn_no = fields.Char('ARN Number')
    filed_status = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="GST Filed Status")
    filing_date = fields.Date('ARN Filing Date')

    _sql_constraints = [
        ('arn_uniq', 'unique (month,year)', 'The GST filing should be unique per month !')
    ]

    @api.onchange('arn_no')
    def _onchange_arn_no(self):
        if self.arn_no and self.filed_status == 'yes':
            CurrMonthInvs = self.env['account.move'].search([]).filtered(lambda x: x.invoice_date and
                                                                                   str(x.invoice_date.month) == self.month and x.state == 'posted')
            if CurrMonthInvs: CurrMonthInvs.write({'arn_id': self._origin.id})


class BSDverify(models.Model):
    _name = 'bs.delivery.verification'

    name = fields.Char('Receiver Person Name')
    mobile = fields.Char('Mobile')
    email = fields.Char('Email')
    comments = fields.Char('Comments')
    otp = fields.Char('otp')
    is_link_send = fields.Boolean(string="Link Sent")
    email_token = fields.Char(string="Token")
    company_id = fields.Many2one('res.company')
    sale_id = fields.Many2one('sale.order')
    partner_id = fields.Many2one('res.partner')
    user_id = fields.Many2one('res.users')
    delivry_person = fields.Char('Delivery person Name')
    delivry_person_contact = fields.Char('Delivery person Contact')
    site_name = fields.Char('Site Name')
    site_location = fields.Char('Site Location')
    landmark = fields.Char('Landmark')

    def send_verification_email(self, emails):
        import hmac
        import hashlib
        base_url = self.env['ir.config_parameter'].sudo().get_param('base.url')
        base_link = 'http://localhost:8069/bs/verified'
        params = {'email': self.email, 'mobile': self.mobile}
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        token = '%s?%s' % (base_link, ' '.join('%s=%s' % (key, params[key]) for key in sorted(params)))
        hm = hmac.new(secret.encode('utf-8'), token.encode('utf-8'), hashlib.sha1).hexdigest()
        email_url = 'http://localhost:8069/bs/verified?code=' + str(self.id) + '&string=' + hm
        subject = _("Delivery Verification Confirmation")
        body = _("""Please click on below link to confirm:
               <a href="%(url)s">%(link)s </a>.
            """, link=hm, url=email_url)
        email = self.env['ir.mail_server'].build_email(
            email_from=self.env.user.company_id.email,
            email_to=emails,
            subject=subject, body=body, subtype='html',
        )
        self.env['ir.mail_server'].send_email(email)
        self.is_link_send = True
        self.email_token = hm
        return True

    def send_info_email(self, emails):
        subject = _("Delivery Confirmation")
        body = _("""
            Dear %s,
            Your order %s delivered at site location:%s, site name:%s .
            Received by %s / %s  .
            If found any suspicious for this order please call us immediately %s
            """ % (self.partner_id.name, self.sale_id.name, self.site_location, self.sitename_id.name if self.sitename_id else '', self.name, self.mobile,
                   '96424 96424'))
        email = self.env['ir.mail_server'].build_email(
            email_from=self.env.user.company_id.email,
            email_to=emails,
            subject=subject, body=body,
        )
        self.env['ir.mail_server'].send_email(email)
        return True

    def get_default_value(self, user, picking):
        picking = self.env['stock.picking'].sudo().search([('delivery_person', '=', user.id), ('id', '=', picking)])
        sale_order = picking.sale_id
        vals = {
            'so_name': sale_order.name,
            'sale_id': sale_order.id,
            'partner_id': sale_order.partner_id.id,
            'partner_name': sale_order.partner_id.name,
            'user_id': user,
            'bs_user_id': user.id,
            'delivry_person': user.name,
            'site_name': sale_order.partner_id.sitename_id.name if sale_order.partner_id.sitename_id else '',
            'site_location': sale_order.partner_id.site_location
        }
        return vals

    def get_default_assign_value(self, user):
        pickings = self.env['stock.picking'].sudo().search([('delivery_person', '=', user.id)])
        list_vals = []
        for picking in pickings:
            sale_order = picking.sale_id
            vals = {
                'so_name': sale_order.name,
                'sale_id': sale_order.id,
                'partner_id': sale_order.partner_id.id,
                'partner_name': sale_order.partner_id.name,
                'user_id': user,
                'bs_user_id': user.id,
                'delivry_person': user.name,
                'site_name': sale_order.partner_id.sitename_id.name if sale_order.partner_id.sitename_id else '',
                'site_location': sale_order.partner_id.site_location,
                'picking_id': picking.id
            }
            list_vals.append(vals)
        return list_vals


class BSSmsLog(models.Model):
    _name = "bs.sms.log"
    _order = "id desc"

    name = fields.Char('SMS Record Name')
    res_id = fields.Char('Related Document ID')
    model = fields.Char('Related Document Model')
    sms_type = fields.Selection([('otp', 'OTP'),
                                 ('trans', 'Transactional')], string='Type')
    subtype = fields.Selection([('signin', 'Sign-In OTP'),
                                ('signup','Sign-Up OTP'),
                                ('reset_pass', 'Reset Password OTP'),
                                ('others', 'Others')], string='Subtype')
    body = fields.Text('SMS')
    sent_time = fields.Datetime('SMS Sent At')
    partner_id = fields.Many2one('res.partner', string='Customer')
    recipient_id = fields.Many2one('res.partner', string='Receipient')
    mobile = fields.Char('Mobile')
    email = fields.Char(string='Email')
    # gateway_id = fields.Many2one('gateway_setup', string='Gateway')
    response = fields.Char('Response')
    otp = fields.Char('OTP')

class BSDistrict(models.Model):
    _name = 'bs.district'

    name = fields.Char('Name')
    state_id = fields.Many2one('res.country.state', string="State")


class BSWebsite(models.Model):
    _inherit = "website"

    #overridden
    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        """ Return the current sales order after mofications specified by params.
        :param bool force_create: Create sales order if not already existing
        :param str code: Code to force a pricelist (promo code)
                         If empty, it's a special case to reset the pricelist with the first available else the default.
        :param bool update_pricelist: Force to recompute all the lines from sales order to adapt the price with the current pricelist.
        :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one
        :returns: browse record for the current sales order
        """
        self.ensure_one()
        partner = self.env.user.partner_id
        sale_order_id = request.session.get('sale_order_id')
        check_fpos = False
        if self.env.user and not sale_order_id and not self.env.user._is_public():
            last_order = partner.last_website_so_id
            if last_order:
                available_pricelists = self.get_pricelist_available()
                # Do not reload the cart of this user last visit if the cart uses a pricelist no longer available.
                sale_order_id = last_order.pricelist_id in available_pricelists and last_order.id
                check_fpos = True

        # Test validity of the sale_order_id
        sale_order = self.env['sale.order'].with_company(request.website.company_id.id).sudo().browse(sale_order_id).exists() if sale_order_id else None

        # Do not reload the cart of this user last visit if the Fiscal Position has changed.
        if check_fpos and sale_order:
            fpos_id = (
                self.env['account.fiscal.position'].sudo()
                .with_company(sale_order.company_id.id)
                .get_fiscal_position(sale_order.partner_id.id, delivery_id=sale_order.partner_shipping_id.id)
            ).id
            if sale_order.fiscal_position_id.id != fpos_id:
                sale_order = None

        if not (sale_order or force_create or code):
            if request.session.get('sale_order_id'):
                request.session['sale_order_id'] = None
            return self.env['sale.order']

        if self.env['product.pricelist'].browse(force_pricelist).exists():
            pricelist_id = force_pricelist
            request.session['website_sale_current_pl'] = pricelist_id
            update_pricelist = True
        else:
            pricelist_id = request.session.get('website_sale_current_pl') or self.get_current_pricelist().id

        if not self._context.get('pricelist'):
            self = self.with_context(pricelist=pricelist_id)

        # cart creation was requested (either explicitly or to configure a promo code)
        if not sale_order:
            # TODO cache partner_id session
            pricelist = self.env['product.pricelist'].browse(pricelist_id).sudo()
            so_data = self._prepare_sale_order_values(partner, pricelist)
            sale_order = self.env['sale.order'].with_company(request.website.company_id.id).with_user(SUPERUSER_ID).create(so_data)

            # set fiscal position
            if request.website.partner_id.id != partner.id:
                sale_order.onchange_partner_shipping_id()
            else: # For public user, fiscal position based on geolocation
                country_code = request.session['geoip'].get('country_code')
                if country_code:
                    country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1).id
                    sale_order.fiscal_position_id = request.env['account.fiscal.position'].sudo().with_company(request.website.company_id.id)._get_fpos_by_region(country_id)
                else:
                    # if no geolocation, use the public user fp
                    sale_order.onchange_partner_shipping_id()

            request.session['sale_order_id'] = sale_order.id

        # case when user emptied the cart
        if not request.session.get('sale_order_id'):
            request.session['sale_order_id'] = sale_order.id

        # check for change of pricelist with a coupon
        pricelist_id = pricelist_id or partner.property_product_pricelist.id

        # check for change of partner_id ie after signup
        if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
            flag_pricelist = False
            if pricelist_id != sale_order.pricelist_id.id:
                flag_pricelist = True
            fiscal_position = sale_order.fiscal_position_id.id

            # change the partner, and trigger the onchange
            sale_order.write({'partner_id': partner.id})
            sale_order.with_context(not_self_saleperson=True).onchange_partner_id()
            sale_order.write({'partner_invoice_id': partner.id})
            sale_order.onchange_partner_shipping_id() # fiscal position
            sale_order['payment_term_id'] = self.sale_get_payment_term(partner)

            # check the pricelist : update it if the pricelist is not the 'forced' one
            values = {}
            if sale_order.pricelist_id:
                if sale_order.pricelist_id.id != pricelist_id:
                    values['pricelist_id'] = pricelist_id
                    update_pricelist = True

            # if fiscal position, update the order lines taxes
            if sale_order.fiscal_position_id:
                sale_order._compute_tax_id()

            # if values, then make the SO update
            if values:
                sale_order.write(values)

            # check if the fiscal position has changed with the partner_id update
            recent_fiscal_position = sale_order.fiscal_position_id.id
            # when buying a free product with public user and trying to log in, SO state is not draft
            if (flag_pricelist or recent_fiscal_position != fiscal_position) and sale_order.state == 'draft':
                update_pricelist = True

        if code and code != sale_order.pricelist_id.code:
            code_pricelist = self.env['product.pricelist'].sudo().search([('code', '=', code)], limit=1)
            if code_pricelist:
                pricelist_id = code_pricelist.id
                update_pricelist = True
        elif code is not None and sale_order.pricelist_id.code and code != sale_order.pricelist_id.code:
            # code is not None when user removes code and click on "Apply"
            pricelist_id = partner.property_product_pricelist.id
            update_pricelist = True

        # update the pricelist
        if update_pricelist:
            request.session['website_sale_current_pl'] = pricelist_id
            values = {'pricelist_id': pricelist_id}
            sale_order.write(values)
            for line in sale_order.order_line:
                if line.exists():
                    sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

        return sale_order


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    partner_bank = fields.Char('Partner Bank', help="This bank account used for refund")

    def name_get(self):
        result = []
        for ticket in self:
            result.append((ticket.id, "%s (#%s)" % (ticket.name, 'BST' + str(ticket._origin.id))))
        return result


# Check if needed
class BSSMSTemplates(models.Model):
    _name = "bs.sms.template"
    _description = 'SMS Template'

    name = fields.Char('Template Name')
    content = fields.Text('Content')
    company_id = fields.Many2one('res.company')
    
class SignupHistory(models.Model):
    _name = "signup.history"
    _description = 'Signup History'

    name = fields.Char('Name')
    email = fields.Char('Email')
    mobile = fields.Char('Mobile')
    signup_time = fields.Datetime('Signup Time')
    user_id = fields.Many2one('res.users')
    company_id = fields.Many2one('res.company')
    customer_type = fields.Char('Customer Type')
    customer_code = fields.Char('Customer Code')
    
class SignupBanner(models.Model):
    _name = "signup.banner"
    _description = 'Signup Banner'
    
    name = fields.Char(string='Description', help="Description of banner.")
    redirecting_url = fields.Char('Redirecting URL', help="URL to redirect to")
    banner_content = fields.Text('Banner Content')
    s3_url = fields.Char('S3 Bucket URL', help="To get image from s3 bucket")
    sequence = fields.Integer('Sequence', help="Sequence")
    image = fields.Image("Image")
    active = fields.Boolean('Active')
    redirecting_url = fields.Char('Redirecting URL', help="URL to redirect to")
