from odoo import api, fields, models
from odoo.http import request
import requests, pyotp
import datetime
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class BSResPartner(models.Model):
    _inherit = "res.partner"

    district_id = fields.Many2one("bs.district", string='District')
    customer_type = fields.Selection([('b2b', 'B2B'),
                                      ('b2c', 'B2C'),], string='Customer Type')
    gst_ids = fields.One2many('bs.gst','partner_id','GSTs')
    is_default_addr = fields.Boolean(help='to set default bill or ship address', default=False)
    site_name = fields.Char('Site Name')
    site_location = fields.Char('Site Location')
    landmark = fields.Char('Landmark')
    default_shipping_id = fields.Many2one('res.partner') #For website
    legal_name = fields.Char(string="Legal Name")
    trade_name  = fields.Char("Trade Name")

    # Customer Specific account details
    partner_code = fields.Char('Partner Code', copy=False, tracking=True)
    bs_acct_no = fields.Char('Bank Account No.', help="Customer specific bank account no. as per buildmart.",
                             copy=False, tracking=True)
    bs_acct_bank_id = fields.Many2one('res.bank','Bank')
    bs_acct_ifsc_code = fields.Char('IFSC Code')
    bs_acct_beneficiary_name = fields.Char('Beneficiary Name', copy=False, tracking=True)
    bs_acct_address = fields.Char('Bank Address')

    to_notify_sms = fields.Boolean('Notify SMS', default=True, tracking=True, copy=False)
    to_notify_email = fields.Boolean('Notify Email', default=True, tracking=True, copy=False)

    sitename_id = fields.Many2one('bs.sitename', 'Site Name')
    maps_location = fields.Char('Location', copy=False)

    _sql_constraints = [
        ('bank_code_uniq', 'unique (bs_acct_no)',"A bank account number with this sequence already exists."),
        ('partner_code_uniq', 'unique (partner_code)', "A partner code with this sequence already exists."),
    ]
    #TODO: name get, name search

    # Overridden
    @api.depends('is_company', 'name', 'parent_id.display_name', 'type', 'company_name', 'partner_code')
    def _compute_display_name(self):
        diff = dict(show_address=None, show_address_only=None, show_email=None, html_format=None, show_vat=None)
        names = dict(self.with_context(**diff).name_get())
        for partner in self:
            partner.display_name = names.get(partner.id)

    # Overridden
    def _get_contact_name(self, partner, name, sitename):
        if sitename:
            return "%s, %s(%s)" % (partner.commercial_company_name or partner.sudo().parent_id.name, sitename, name)
        else:
            return "%s, %s" % (partner.commercial_company_name or partner.sudo().parent_id.name, name)

    # Overridden
    def _get_name(self):
        partner = self
        name = partner.name or ''
        if partner.bs_acct_no: name = '[' + str(partner.bs_acct_no) + ']' + str(name)

        if partner.company_name or partner.parent_id:
            if not name and partner.type in ['invoice', 'delivery', 'other']:
                name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
            if not partner.is_company:
                name = self._get_contact_name(partner, name, partner.sitename_id.name if partner.sitename_id else '')
        if self._context.get('show_address_only'):
            name = partner._display_address(without_company=True)
        if self._context.get('show_address'):
            name = name + "\n" + partner._display_address(without_company=True)
        name = name.replace('\n\n', '\n')
        name = name.replace('\n\n', '\n')
        if self._context.get('partner_show_db_id'):
            name = "%s (%s)" % (name, partner.id)
        if self._context.get('address_inline'):
            splitted_names = name.split("\n")
            name = ", ".join([n for n in splitted_names if n.strip()])
        if self._context.get('show_email') and partner.email:
            name = "%s <%s>" % (name, partner.email)
        if self._context.get('html_format'):
            name = name.replace('\n', '<br/>')
        if self._context.get('show_vat') and partner.vat:
            name = "%s ‒ %s" % (name, partner.vat)
        return name

    def _verify_pending_contacts(self):
        PendingContacts = self.search([('parent_id', '=', False), ('partner_code', '=', '')])
        if not PendingContacts: return

        EmailContent = '<p>Dear Admin,</p><p>Below is the list of contacts that needs to be verified,</p><br/>'
        PendingContactsInfo = '<table><tr><th>ID</th><th>Name</th><th>Email</th><th>Mobile</th></tr>'
        for rec in PendingContacts:
            PendingContactsInfo += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'\
                                   %(rec.id, rec.name, rec.email, rec.mobile)
        PendingContactsInfo += '</table><br/>'
        EmailContent += PendingContactsInfo + '<p>Regards,</p><p>buildmart</p>'

        #TODO trigger email

    def verify_contact(self):
        print(self)
        for partner in self:
            if not partner.parent_id and not partner.partner_code:
                if partner.supplier_rank > partner.customer_rank:
                    partner.partner_code = self.env['ir.sequence'].next_by_code('bs.vendor.code')
                else:
                    if partner.customer_type == 'b2c':
                        partner.partner_code = self.env['ir.sequence'].next_by_code('bs.b2c.code')
                    else:
                        if partner.company_type == 'company' and partner.vat:
                            partner.partner_code = self.env['ir.sequence'].next_by_code('bs.partner.code')
            if (partner.partner_code) and not partner.bs_acct_no and self.env.company.corporate_code:
                partner.bs_acct_no = self.env.company.corporate_code + partner.partner_code
                partner.bs_acct_bank_id = self.env.company.bank_id.id
                partner.bs_acct_ifsc_code = self.env.company.ifsc_code
                partner.bs_acct_address = self.env.company.bank_address
                partner.bs_acct_beneficiary_name = partner.name

    # def write(self, vals):<!-- Will be generated only from verify-->
    #     res = super(BSResPartner, self).write(vals)
    #     for rec in self:
    #         if not rec.parent_id and not self.bs_acct_no: rec.generate_ban_code()  # Generates Partner & BS account code
    #     return res

    def _display_address(self, without_company=False):
        address_format = super()._get_address_format()
        args = {
            'bs_acct_no': self.bs_acct_no or self.partner_code or '',
            'state_code': self.state_id.l10n_in_tin or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            'company_name': self.commercial_company_name or '',
        }
        for field in super()._formatting_address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '\033[1m' + '%(company_name)s\n' + '\033[1m' + address_format
        return address_format % args

    @api.model
    def update_address(self, vals):
        if vals.get('addr_id', False):
            pid = int(vals.get('addr_id'))
            del vals['addr_id']
            partner = self.browse(pid)
            partner.write(vals)
        return True

    @api.model
    def removeAddr(self, vals):
        try:
            partner = self.browse(int(vals.get('addr_id')))
            if partner:
                partner.unlink()
                return True
            return False

        except Exception as e:
            return e

    @api.model
    def setDefaultAddr(self, vals):
        pid = int(vals.get('addr_id'))
        partner = self.browse(pid)
        removeDefault = self.search([('type', '=', partner.type), ('parent_id', '=', partner.parent_id.id)])
        removeDefault.is_default_addr = False
        partner.is_default_addr = True
        return True

    def send_otp(self, User, OTPType, Type, NonUserVal):

        Company = self.env.company or self.env['res.company'].browse(1)
        MobVal, EmailVal = '', ''
        OutgSMS = bool(self.env['ir.config_parameter'].sudo().get_param('bs.outgng_sms', False))
        OutgMail = bool(self.env['ir.config_parameter'].sudo().get_param('bs.outgng_mail', False))
        BSOTPExpTime = int(request.env['ir.config_parameter'].sudo().get_param('bs.otp_expiry_time', 90))
        if Type == 'email':
            totp = request.session.get('eotpobj')
            # if not (totp and ((datetime.now() - totp.time_generated).total_seconds() < BSOTPExpTime)):
            base32Code = pyotp.random_base32()
            totp = pyotp.TOTP(base32Code, interval=2700)
            request.session['eotpobj'] = totp
            totp.time_generated = datetime.now()
            OTP = totp.now()
            print(OTP)
        else:
            totp = request.session.get('motpobj')
            # if not (totp and ((datetime.now() - totp.time_generated).total_seconds() < BSOTPExpTime)):
            base32Code = pyotp.random_base32()
            totp = pyotp.TOTP(base32Code, interval=2700)
            request.session['motpobj'] = totp
            totp.time_generated = datetime.now()
            OTP = totp.now()
            print(OTP)
        
        Response = False

        if Type == 'email': EmailVal = User.login or User.partner_id.email if User else NonUserVal
        if Type == 'mobile': MobVal = User.partner_id.mobile if User else NonUserVal
        if Type == 'verify': MobVal = User.partner_id.mobile if User else NonUserVal

        if OTPType == 'login':
            SMSTemplate = self.env.ref('buildmart.bs_login_otp').content
            template = self.env.ref('buildmart.bs_email_otp', raise_if_not_found=False).sudo()
        elif OTPType == 'signup':
            SMSTemplate = self.env.ref('buildmart.bs_signup_otp').content
            template = self.env.ref('buildmart.bs_email_signup_otp', raise_if_not_found=False).sudo()
        elif OTPType == 'reset_password':
            SMSTemplate = self.env.ref('buildmart.bs_reset_pass_otp').content
            template = self.env.ref('buildmart.bs_reset_password_email', raise_if_not_found=False).sudo()
        else:
            SMSTemplate = False
            template = False

        Response = False
        try:
            Message = ''
            if Type == 'mobile' and SMSTemplate and MobVal:
                Message = str(SMSTemplate) % ('mobile', OTP, BSOTPExpTime, Company.phone)
                sms_provider = self.env['sms.provider'].search([('active_provider','=',True)], limit=1)
                if sms_provider.name == 'VI':
                    url = "https://cts.myvi.in:8443//ManageSms/api/sms/Createsms/json/apikey=%s" % (sms_provider.sms_apikey)
                    headers = {'Authorization': 'Bearer %s' % (sms_provider.get_sms_token())}
                    params = {
                        "msisdn": MobVal,
                        "sms": Message,
                        "unicode": "0",
                        "senderid": sms_provider.sms_senderid,
                        "pingbackurl": "https://buildmart.com/pingback/sms"
                    }
                    if OutgSMS:
                        Response = requests.post(url, params, headers=headers)
                if sms_provider.name == 'webking':
                    url = "%s?username=%s&pass=%s&senderid=%s&message=%s&dest_mobileno=%s&msgtype=TXT&response=Y" % (
                        sms_provider.access_point,sms_provider.sms_username,sms_provider.sms_password,sms_provider.sms_senderid,Message,MobVal)
                    if OutgSMS:
                        Response = requests.post(url)

            elif Type == 'email' and SMSTemplate and EmailVal:
                subject = (OTPType.title() + ' OTP') if not OTPType == 'reset_password' else 'Reset Password'
                Message = str(SMSTemplate) % ('email', OTP, BSOTPExpTime, Company.phone)
                mail_values = {'email_from': 'info@buildmart.com',
                               'email_to': EmailVal,
                                'subject': subject,
                                'body_html': Message,
                                'state': 'outgoing'
                }
                if OutgMail and template:
                    Response = template.send_mail(Company.id, force_send=True, raise_exception=True, email_values=mail_values)
                    _logger.info("reset password email sent")

            elif Type == 'verify' and SMSTemplate and MobVal:
                Message = str(SMSTemplate) % ('mobile', OTP, BSOTPExpTime, Company.phone)
                sms_provider = self.env['sms.provider'].search([('active_provider','=',True)], limit=1)
                if sms_provider.name == 'VI':
                    url = "https://cts.myvi.in:8443//ManageSms/api/sms/Createsms/json/apikey=%s" % (sms_provider.sms_apikey)
                    headers = {'Authorization': 'Bearer %s' % (sms_provider.get_sms_token())}
                    params = {
                        "msisdn": MobVal,
                        "sms": Message,
                        "unicode": "0",
                        "senderid": sms_provider.sms_senderid,
                        "pingbackurl": "https://buildmart.com/pingback/sms"
                    }
                    Response = requests.post(url, params, headers=headers)
                    Response = {'response': Response, 'otp': OTP}
                if sms_provider.name == 'webking':
                    url = "%s?username=%s&pass=%s&senderid=%s&message=%s&dest_mobileno=%s&msgtype=TXT&response=Y" % (
                        sms_provider.access_point,sms_provider.sms_username,sms_provider.sms_password,sms_provider.sms_senderid,Message,MobVal)
                    Response = requests.post(url)
                    Response = {'response': Response, 'otp': OTP}
        except Exception as e:
            print('Exception --- ', e)

        finally:
                self.env['bs.sms.log'].sudo().create({'res_id': User.id if User else False, 'model': 'res.users',
                                                      'sms_type': 'otp', 'subtype': 'signin', 'body': Message,
                                                      'sent_time': datetime.now(),
                                                      'recipient_id': User.partner_id.id if User else False,
                                                      'email': EmailVal,
                                                      'mobile': MobVal,
                                                      'response': Response, 'otp': OTP})
                return Response



    # def generate_ban_code(self):
    #     for rec in self:
    #         if not rec.parent_id:
    #             if not rec.partner_code:
    #                 if rec.supplier_rank > rec.customer_rank:
    #                     rec.partner_code = self.env['ir.sequence'].next_by_code('bs.vendor.code')
    #                 else:
    #                     if rec.customer_type == 'b2c':
    #                         rec.partner_code = self.env['ir.sequence'].next_by_code('bs.b2c.code')
    #                     else:
    #                         if rec.company_type == 'company' and rec.vat:
    #                             rec.partner_code = self.env['ir.sequence'].next_by_code('bs.partner.code')
    #
    #             if rec.partner_code and not rec.bs_acct_no and self.env.company.corporate_code:  # rec.company_type == 'company' and rec.vat -- removed
    #                 rec.bs_acct_no = self.env.company.corporate_code + rec.partner_code
    #                 rec.bs_acct_bank_id = self.env.company.bank_id.id
    #                 rec.bs_acct_ifsc_code = self.env.company.ifsc_code
    #                 rec.bs_acct_address = self.env.company.bank_address
    #                 rec.bs_acct_beneficiary_name = rec.name

    # ---TODO:check if needed now---------VENDOR ---- STARTS --------------------

    @api.model
    def redirect_action(self, args):
        action = self.env.ref('buildmart.purchase_rfq_vendor')
        action.sudo().domain = [('partner_id', '=', self.env.user.partner_id.id), ('state', '=', 'draft')]
        url = '/web#action=' + str(action.id) + '&model=purchase.order&view_type=list&cids=1&menu_id=340'
        return url

    @api.model
    def redirect_action_confirm(self, args):
        action = self.env.ref('buildmart.purchase_confirm_vendor')
        action.sudo().domain = [('partner_id', '=', self.env.user.partner_id.id), ('state', '=', 'purchase')]
        url = '/web#action=' + str(action.id) + '&model=purchase.order&view_type=list&cids=1&menu_id=340'
        return url

    @api.model
    def redirect_action_cancel(self, args):
        action = self.env.ref('buildmart.purchase_cancel_vendor')
        action.sudo().domain = [('partner_id', '=', self.env.user.partner_id.id), ('state', '=', 'cancel')]
        url = '/web#action=' + str(action.id) + '&model=purchase.order&view_type=list&cids=1&menu_id=340'
        return url
    # ------------VENDOR ---- ENDS --------------------


class BSResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    ifsc_code = fields.Char(string="IFSC Code")
    bank_address = fields.Text(string="Bank Address")
    bank_attachment_id = fields.Many2one('ir.attachment', string="Cancelled Cheque or Bank Statement")
    is_default = fields.Boolean('Is Default ?')


#Todo: check what is no longer needed
class BSGSTDetails(models.Model):
    _name = "bs.gst"

    name = fields.Char('GSTIN')
    pan = fields.Char('PAN')
    registered_address = fields.Text('Registered Address')
    legal_name = fields.Char('Legal Name')
    trade_name = fields.Char('Trade Name')
    reg_date = fields.Date('Registered On')
    gst_updated_date = fields.Date('Last Updated On')
    api_response = fields.Text('API Response')
    gst_status = fields.Selection([('active','Active'),('inactive','InActive')], 'GST Status')
    city = fields.Char('City')
    state_id = fields.Many2one('res.country.state', string="State")
    district_id = fields.Many2one('bs.district', string="District")
    pincode = fields.Char('Pincode')
    default = fields.Boolean("Default GSTIN")
    partner_id = fields.Many2one('res.partner', 'B2B Customer')
    mobile = fields.Char('Mobile')

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'GSTIN already exists')
    ]


class BSSiteName(models.Model):
    _name = "bs.sitename"

    name = fields.Char('Sitename')
    company_id = fields.Many2one('res.partner',
                                 domain="[('is_company','=', True)]",
                                 copy=False,)

    _sql_constraints = [
        ('unique_compny_sitename', 'unique (name, company_id)', 'Given sitename for this company already exists!')
    ]
