from odoo import api, fields, models, _
import requests

class BSResCompany(models.Model):
    _inherit = 'res.company'

    #GST API
    gst_url = fields.Char('GST URL', help="URL that API hits to for response, storing it for change from their end")
    gst_agent_key = fields.Char('Agent Key', help="Agent key will be available in GST portal dashboard.")
    gst_pre_prod_key = fields.Char('Pre Production Key', help="Generate pre-production key under GST portal. This will be only for test purpose.")
    gst_prod_key = fields.Char('Production Key', help="Generate production key under GST portal.")

    # Customer Care / Service
    cust_care_phone = fields.Char('Phone', help="Customer Care number that customers can reach to.")
    cust_care_email = fields.Char('Email', help="Customer Care email that customers can email to.")

    corporate_code = fields.Char('Corporate Code')
    # NEFT/RTGS
    bank_id = fields.Many2one('res.bank', 'Bank')
    ifsc_code = fields.Char('IFSC Code')
    bank_address = fields.Char('Bank Address')

    #SMS OTP
    sms_provider_ids = fields.One2many('sms.provider','company_id','SMS Provider')
    sms_username = fields.Char('Username')
    sms_password = fields.Char('Password')
    sms_senderid = fields.Char('Sender ID', help="Should be whitelisted.")
    sms_apikey = fields.Char('API Key')
    # sms_template_ids = fields.One2many('bs.sms.template', 'company_id', 'SMS Templates')
    email_logo = fields.Image("Email Logo")

    old_address_ids = fields.One2many('bs.old.address','company_id','Old Address')

    def get_sms_token(self):
        if self.sms_username and self.sms_password:
            response = requests.post('https://cts.myvi.in:8443/ManageSms/api/AuthJwt/Authenticate',
                                 data={'username': self.sms_username, 'password':self.sms_password})
            if response: return response.json()
        return ""

class BSOldAddress(models.Model):
    _name = "bs.old.address"

    name = fields.Char('Short Name')
    address = fields.Html('Address')
    date_from = fields.Date('From')
    date_to = fields.Date('To')
    company_id = fields.Many2one('res.company')
    
class BSSMSProvider(models.Model):
    _name = "sms.provider"

    name = fields.Char('Name')
    sms_username = fields.Char('Username')
    sms_password = fields.Char('Password')
    access_point = fields.Char('Access Point')
    sms_senderid = fields.Char('Sender ID', help="Should be whitelisted.")
    sms_apikey = fields.Char('API Key')
    company_id = fields.Many2one('res.company')
    active_provider = fields.Boolean(default=False)
    
    def active_sms_provider(self):
        all_providers = self.env['sms.provider'].search([])
        all_providers.write({'active_provider':False})
        self.active_provider = True