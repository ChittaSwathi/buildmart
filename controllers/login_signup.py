import odoo
from odoo.addons.website.controllers.main import Home
from odoo.exceptions import UserError
from odoo.addons.web.controllers.main import ensure_db
from odoo.service import security
from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from odoo.addons.auth_signup.models.res_users import SignupError
import logging
_logger = logging.getLogger(__name__)
import werkzeug
import datetime
from datetime import datetime
import requests, json
import random

class BSSignup(AuthSignupHome):

    # ovrridden
    def do_signup(self, qcontext):
        """ Shared helper that creates a res.partner out of a token """
        qcontext.update({'name': qcontext.get('fname', '') + ' ' + qcontext.get('lname', ''),
                         'login': qcontext.get('email') or qcontext.get('mobile'),
                         'customer_type': 'b2b' if qcontext.get('b2b') == 'on' else 'b2c',
                         'password': qcontext.get('password') or qcontext.get('confirm_password')})
        values = {key: qcontext.get(key) for key in ('login', 'name', 'password', 'customer_type')}
        if not values:
            raise UserError(_("The form was not properly filled in."))
        values['groups_id'] = [(6, 0, [request.env.ref('base.group_portal').id])]
        supported_lang_codes = [code for code, _ in request.env['res.lang'].get_installed()]
        lang = request.context.get('lang', '').split('_')[0]
        if lang in supported_lang_codes: values['lang'] = lang
        self._signup_with_values(qcontext.get('token'), values)

        User = request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))])
        CompanyRec, DistrictID, StateID = False, False, False
        if qcontext.get('district_id', False):
            if int(qcontext.get('district_id')) != 0:
                DistrictID = int(qcontext.get('district_id'))
            elif int(qcontext.get('gst_district_id')) != 0:
                DistrictID = int(qcontext.get('gst_district_id'))
        if qcontext.get('state_id', False):
            if int(qcontext.get('state_id')) != 0:
                StateID = int(qcontext.get('state_id'))
            elif int(qcontext.get('gst_state_id')) != 0:
                StateID = int(qcontext.get('gst_state_id'))

        if User:
            AcctAcctObj = request.env['account.account'].sudo()

            AcctRecvRec = AcctAcctObj.search([('user_type_id.type', '=', 'receivable'),('code','=','720010')])\
                .filtered(lambda x: 'B2C' in x.name)
            AcctPayRec = AcctAcctObj.search([('user_type_id.type', '=', 'payable'),('code','=','220010')]).\
                filtered(lambda x: 'B2C' in x.name)
            Contact, Company = {'customer_type': 'b2c',
                                'email': qcontext.get('email') or qcontext.get('login'),
                                'zip': qcontext.get('zip'),
                                'city': qcontext.get('city'),
                                'district_id': DistrictID,
                                'state_id': StateID,
                                'mobile': request.env['res.partner']._phone_format(qcontext.get('mobile')),
                                'property_account_receivable_id':AcctRecvRec.id if AcctRecvRec else False,
                                'property_account_payable_id': AcctPayRec.id if AcctPayRec else False}, {}
            if qcontext.get('b2b') == 'on':
                CustTags = []
                AcctRecvRec = AcctAcctObj.search([('user_type_id.type','=','receivable'),('code','=','720020')])\
                    .filtered(lambda x:'B2B' in x.name)
                AcctPayRec = AcctAcctObj.search([('user_type_id.type','=','payable'),('code','=','220020')]).\
                    filtered(lambda x:'B2B' in x.name)
                Company.update({'company_type': 'company', 'is_company': True})

                if qcontext.get('builder') == 'on': CustTags += [request.env.ref('buildmart.builder_id').id]
                if qcontext.get('rmc') == 'on': CustTags += [request.env.ref('buildmart.rmc_id').id]
                if qcontext.get('manufacturer') == 'on': CustTags += [
                    request.env.ref('buildmart.manufacturer_id').id]
                if qcontext.get('dealer') == 'on': CustTags += [request.env.ref('buildmart.dealer_id').id]
                if qcontext.get('others') == 'on': CustTags += [request.env.ref('buildmart.others_id').id]
                Company.update({'category_id': [(6, 0, CustTags)]})

                Company.update({'vat': qcontext.get('gstin').strip(),
                                'state_id': StateID,
                                'district_id': DistrictID,
                                'city': qcontext.get('gst_city'),
                                'zip': qcontext.get('gst_zip'),
                                'street': qcontext.get('reg_address'),
                                'name': qcontext.get('shop_name'),  # trade name
                                'legal_name': qcontext.get('legal_name'),
                                'l10n_in_gst_treatment': 'regular',
                                'company_type':'company',
                                'property_account_receivable_id': AcctRecvRec.id if AcctRecvRec else False,
                                'property_account_payable_id': AcctPayRec.id if AcctPayRec else False
                                })
                CompanyRec = request.env['res.partner'].sudo().search([('vat', '=', qcontext.get('gstin', '').strip())],
                                                                      limit=1)
                if not CompanyRec:
                    CompanyRec = request.env['res.partner'].sudo().create(Company)
                else:
                    CompanyRec.write(Company)

            if CompanyRec:
                Contact.update({'customer_type': 'b2b', 'type': 'contact', 'parent_id': CompanyRec.id})
            
            
            User.partner_id.sudo().write(Contact)
            request.env['signup.history'].sudo().create({
                'name':User.partner_id.name,
                'mobile':User.partner_id.mobile,
                'email':User.partner_id.email,
                'user_id':User.id,
                'customer_type':User.partner_id.customer_type,
                'customer_code':User.partner_id.partner_code,
                'signup_time':datetime.now()
            })
        request.env.cr.commit()

    def get_user_id(self, Type, Value):
        '''Returns user id based on the type (email/mobile) and its respective value'''
        if Type and Value:
            if Type == 'email':
                User = request.env['res.users'].sudo().search([('login', '=', Value)], limit=1)
            else:  # mobile
                if len(Value) == 10:
                    Value = ' '.join([Value[i:i+5] for i in range(0, len(Value), 5)])
                    Value = '+91 '+Value
                User = request.env['res.users'].sudo().search([('login', '=', Value)],limit=1)  # if user uses mobile to login
                if not User: User = request.env['res.users'].sudo().search([('partner_id.mobile', '=', Value)], limit=1)
            return User
        else: return False

    @http.route('/bs/default/address', type='json', auth="user", sitemap=False, website=True)
    def bs_signup_address(self, **kw):
        Partner = request.env.user.partner_id
        return Partner.sudo().write(kw)
    
    @http.route('/signup/banner', type='json', auth="none", sitemap=False, website=True)
    def bs_login_banner(self, **kw):
        bann = request.env['signup.banner'].search([], limit=1)
        html = ''
        if bann:
            banner = random.choice(request.env['signup.banner'].search([]))
            con = banner.banner_content
            if con:
                con.strip()
                html = """<a href='"""+banner.redirecting_url+"""'><img src='"""+banner.s3_url+"""' alt='"""+banner.name+"""'/></a></br>"""
                html += """<span><a href='"""+banner.redirecting_url+"""'>"""+con+"""</a></span>"""
        return {'content': html}
    
    @http.route('/send/login/otp', type='json', auth="none", sitemap=False, website=True)
    def bs_send_login_otp(self, **kw):
        print('send login otp', kw)
        Value, Type, OTPType = kw.get('login', False), kw.get('type', False), kw.get('otp_type', False)
        User = self.get_user_id(Type, Value)
        if User:
            OTPSent = request.env['res.partner'].send_otp(User, OTPType, Type, Value)
            if OTPSent:
                return {'uid': User.id, 'error': ''}  # TODO:check otp response
            else:
                return {'uid': User.id, 'error': 'Something went wrong !!'}
        else:
            return {'uid': False, 'error': 'Account Not Found. Please signup !!'}

    @http.route('/send/signup/otp', type='json', auth="none", sitemap=False, website=True)
    def bs_send_signup_otp(self, **kw):
        print('send signup otp', kw)
        Value, Type, OTPType = kw.get('login', False), kw.get('type', False), kw.get('otp_type', False)
        User = self.get_user_id(Type, Value)
        if User:
            return {'uid': User.id, 'error': 'Account already exists. Please login !!'}
        else:
            OTPSent = request.env['res.partner'].send_otp(False, OTPType, Type, Value)
            if OTPSent:
                return {'uid': False, 'error': ''}
            else:
                return {'uid': False, 'error': 'Something went wrong !!'}
    
    @http.route('/send/reset_password/otp', type='json', auth="none", sitemap=False, website=True)
    def bs_send_reset_otp(self, **kw):
        print('send signup otp', kw)
        Value, Type, OTPType = kw.get('login', False), kw.get('type', False), kw.get('otp_type', False)
        OTPSent = request.env['res.partner'].send_otp(False, OTPType, Type, Value)
        if OTPSent:
            return {'uid': False, 'error': ''}
        else:
            return {'uid': False, 'error': 'Something went wrong !!'}

    @http.route(['/bs/validate/otp'], type='json', auth="public", methods=['POST'], sitemap=False, website=True)
    def verify_otp(self, otp=False, otptype=False):
        if otptype == 'email':
            totp = request.session.get('eotpobj')
        else:
            totp = request.session.get('motpobj')
        BSOTPExpTime = int(request.env['ir.config_parameter'].sudo().get_param('bs.otp_expiry_time', 90))
        if totp:
            TotalSecs = (datetime.now() - totp.time_generated).total_seconds()
            if TotalSecs < BSOTPExpTime:
                return totp.verify(otp)
            else:
                return False  # OTPExpired
        else:
            return False  # OTPNotFound in session
        
    @http.route(['/update/password'], type='json', auth="public", methods=['POST'], sitemap=False, website=True)
    def password_update(self, **post):
        print(post)
        msg = 'not_update'
        totp = request.session.get('otpobj')
        otp = post.get('code', False)
        if otp:
            valid = totp.verify(otp)
            if valid:
                password = post.get('password', False)
                login = post.get('email', False)
                if login:
                    user = request.env['res.users'].sudo().search([('login', '=', login)], limit=1)
                    if not user:
                        user = request.env['res.users'].sudo().search([('partner_id.mobile', '=', login)], limit=1)
                    if user:
                        user.password = password
                        msg = 'update'
                    else:
                        msg = 'not_user'
                else:
                    return {'result':msg}
            else:
                return {'result':msg}
        return {'result':msg}

    @http.route('/bs/user/login', type='json', auth="none", sitemap=False, website=True)
    def user_login(self, **kw):
        return http.local_redirect(self._login_redirect(kw.get('uid')), keep_hash=True)

    @http.route('/bs/user/authenticate', type='json', auth="none", sitemap=False, website=True)
    def bs_user_authenticate(self, **kw):
        """ Validates and authenticates if a user account exists or not, based on both email and mobile """
        db, login, password, type = kw.get('db', request.env.cr.dbname), kw.get('login'), kw.get('password'), kw.get(
            'type', 'email')
        RedirectingURL = kw.get('url').split('?redirect=')[-1] \
            if (kw.get('url', '') and '?redirect=' in kw.get('url', '')) else ''

        if db and login and password:
            if type == 'email':
                User = request.env['res.users'].sudo().search([('login', '=', login)], limit=1)
            else:  # mobile
                if len(login) == 10:
                    login = ' '.join([login[i:i+5] for i in range(0, len(login), 5)])
                    login = '+91 '+login
                User = request.env['res.users'].sudo().search([('login', '=', login)],
                                                              limit=1)  # if user uses mobile to login
                if not User: User = request.env['res.users'].sudo().search([('partner_id.mobile', '=', login)], limit=1)

            # if not User.partner_id.zip: RedirectingURL = '/my/address'
            if User:
                try:
                    Response = {'uid': request.session.authenticate(db, User.login, password), 'error': '',
                                'redirect_url': RedirectingURL}
                except:
                    Response = {'uid': User.id, 'error': 'Invalid Credentials', 'redirect_url': ''}
            else:
                Response = {'uid': False, 'error': 'Account Not Found!', 'redirect_url': ''}
        return Response


class BSWebHome(Home):

    #Overridden
    def _login_redirect(self, uid, redirect=None):
        """ Redirect regular users (employees) to the backend) and others to
        the frontend
        """
        if not redirect and request.params.get('login_success'):
            if request.env['res.users'].browse(uid).has_group('base.group_user'):
                r = request.httprequest.query_string.decode()
                if r == 'redirect=undefined':
                    redirect = '/web'
                else:
                    redirect = '/web?' + r
            elif request.env['res.users'].browse(uid).has_group('base.group_portal'):
                redirect = '/'
            else:
                redirect = '/my'
        return super()._login_redirect(uid, redirect=redirect)

    # Overridden
    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw) :#TODO:remove values
        Partner = request.env.user.partner_id
        homepageRec = request.env['bs.homepage'].sudo().search([('company_id', '=', request.env.company.id)], limit=1)
        best_selling = request.env['product.template'].sudo().search([('is_best_selling', '=', True)], order='web_display_seq desc')
        hot_deals = request.env['product.template'].sudo().search([('is_hot_deal', '=', True)], order='web_display_seq desc')
        sellers = request.env['res.partner'].sudo().search([('supplier_rank', '>=', 1)])
        brands = request.env['product.attribute.value'].sudo().search(
            [('attribute_id', '=', request.env.ref('buildmart.brand_attribute').id),
             ('customer_type', 'in', [Partner.customer_type, 'both'])])
        ClientReviews = request.env['bs.client.review'].sudo().search([])
        values = {'best_selling':best_selling,
                  'hot_deals':hot_deals,
                  'sellers':sellers,
                  'brands':brands,
                  'homepage': homepageRec,
                  'banner_ids': homepageRec.banner_ids if homepageRec else False,
                  'client_reviews' : [ClientReviews[i * 2:(i + 1) * 2] for i in range((len(ClientReviews) + 2 - 1) // 2 )],
                  'AllClientReviews': ClientReviews,
                  }
        return request.render('buildmart.bs_homepage', values)

    @http.route('/web/login', type='http', auth="none", csrf=False)
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None
        AllStates = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'IN')])
        AllDistricts = request.env['bs.district'].sudo().search([])
        values['state_ids'] = AllStates
        values['district_ids'] = AllDistricts
        AllCountry = request.env['res.country'].sudo().search([])
        values['country_code'] = AllCountry    
        if request.httprequest.method == 'POST':
            old_uid = request.uid
            try:
                if request.params['password'] and not request.params.get('otp', False):
                    uid = request.session.authenticate(request.session.db,
                                           request.params.get('login') or request.params.get('email') or request.params.get('mobile'),
                                           request.params.get('password'))
                if not request.params['password'] or (request.params['password'] and request.params.get('otp', False) == 'mobile_otp'):
                    if request.params['first'] and request.params['second'] and request.params['third'] and \
                            request.params['fourth'] and request.params['five'] and request.params['six']:
                        otp = request.params['first'] + request.params['second'] + request.params['third'] + \
                              request.params['fourth'] + request.params['five'] + request.params['six']
                        wsgienv = request.httprequest.environ
                        env = dict(
                            base_location=request.httprequest.url_root.rstrip('/'),
                            HTTP_HOST=wsgienv['HTTP_HOST'],
                            REMOTE_ADDR=wsgienv['REMOTE_ADDR'],
                        )
                        uid = odoo.registry(request.session.db)['res.users'].authenticate_otp(request.session.db,
                                                                                              request.params['email'],
                                                                                              otp, env)
                        request.session.rotate = True
                        request.session.db = request.session.db
                        request.session.uid = uid
                        request.session.login = request.params['email']
                        request.session.session_token = uid and security.compute_session_token(request.session,
                                                                                               request.env)
                        request.uid = uid
                        request.disable_db = False

                        if uid: request.session.get_context()
                request.params['login_success'] = True
                request.params['redirect'] = '/'
                print(request.params)
                return request.redirect(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        if request.session.get('uid'):
            return False

        response = request.render('auth_signup.signup', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route('/web/signup', type='http', auth='public', csrf=False, website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        qcontext.update(kw)
        if request.session.get('uid'):
            return request.redirect('/')
        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)
                # Send an account creation confirmation email
                # if qcontext.get('token'):
                User = request.env['res.users']
                user_sudo = User.sudo().search(
                    User._get_login_domain(qcontext.get('login')), order=User._get_login_order(), limit=1
                )
                template = request.env.ref('auth_signup.mail_template_user_signup_account_created',
                                           raise_if_not_found=False)
                if user_sudo and template:
                    template.sudo().with_context(
                        lang=user_sudo.lang,
                        auth_login=werkzeug.url_encode({'auth_login': user_sudo.email}),
                    ).send_mail(user_sudo.id, force_send=True,email_values={'email_cc':'info@buildmart.com'})
                return self.web_login(*args, **kw)
            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                if request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))]):
                    qcontext["error"] = _("Another user is already registered using this email address.")
                else:
                    _logger.error("%s", e)
                    qcontext['error'] = _("Could not create a new account.")
        AllStates = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'IN')])
        AllDistricts = request.env['bs.district'].sudo().search([])
        qcontext['state_ids'] = AllStates
        qcontext['district_ids'] = AllDistricts

        response = request.render('auth_signup.signup', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    #Todo
    @http.route('/web/reset/password', type='http', auth='public', website=True, sitemap=False)
    def bs_reset_password(self, **kw):
        Values = {}
        return request.render('buildmart.bs_reset_password', Values)

    @http.route('/signup/districts', type='json', auth="public", sitemap=False, website=True)
    def bs_control_signup_districts(self, StateID, **kw):
        if StateID:
            return request.env['bs.district'].sudo().search([('state_id', '=', int(StateID))]).mapped('id')
        return request.env['bs.district'].sudo().search([]).mapped('id')

    @http.route('/change/address/shipping', type='json', auth="public", sitemap=False, website=True)
    def bs_change_shipping_add(self, **kw):
        if kw.get('partner_id') and kw.get('default_shipping_id'):
            request.env['res.partner'].sudo().browse(int(kw.get('partner_id'))).write(
                {'default_shipping_id': int(kw.get('default_shipping_id', 'partner_id'))})

    @http.route('/bs/gst/verify', type='json', auth="none", sitemap=False, website=True)
    def bs_gst_verify(self, **kw):
        '''
            GST API verifies the provided GSTIN and returns the response with all valid detailed respective to the same.
            To reduce charge per hit, we will store every GST input in our database, so that we can return the same if exists else hit the actual API
        '''
        Company = request.env['res.company'].sudo().search([],limit=1)
        GSTIN = str(kw.get('gstin','')).strip()
        APIKey = Company.gst_prod_key or Company.gst_pre_prod_key
        AgencyKey = Company.gst_agent_key
        URL = Company.gst_url

        if GSTIN and URL and AgencyKey and APIKey:

            # Check if API for the same GST was hit before (stores every API hit in database to reduce cost per hit)
            GSTExists = request.env['bs.gst'].sudo().search([('name','=',GSTIN)], limit=1)
            City, District, State, Pincode, FullAdd, TradeName, LegalName = '', '', '', '', '','',''
            StateID, DistrictID =  False, False

            if not GSTExists:
                # ---------- GST API --------------
                url = "%s/verify-gst-lite"%(URL)
                payload = "{\n    \"gstin\":\"%s\",\n    \"consent\":\"Y\",\n    \"consent_text\":\"I have given full consent\"\n} "%(GSTIN)
                headers = { 'Content-Type': 'application/json', 'qt_api_key': APIKey, 'qt_agency_id': AgencyKey }
                response = requests.request("POST", url, headers=headers, data=payload)
                res = json.loads(response.text.encode('utf8')).get('result',{})
                # ---------- GST API --------------

                if res :
                    GSTStatus = res.get('sts')
                    TradeName, LegalName = res.get('tradeNam'), res.get('lgnm')
                    GSTLastUpdated, GSTReg = res.get('lstupdt'), res.get('rgdt')
                    Add = res.get('pradr') and res.get('pradr').get('addr', {})

                    if Add:
                        City, District, State, Pincode = Add['city'], Add['dst'], Add['stcd'], Add['pncd']
                        StateID = request.env['res.country.state'].sudo().search([('name','=',State.strip()),('country_id.code','=','IN')],limit=1).id
                        DistrictID = request.env['bs.district'].sudo().search([('name','=',District.strip()),('state_id','=',StateID)],limit=1).id
                        if not DistrictID: DistrictID = request.env['bs.district'].sudo().create({'name':District.strip(),'state_id':StateID}).id

                        if Add['flno']: FullAdd += Add['flno']
                        if Add['bno']: FullAdd += (', ' if Add['flno'] else '') + Add['bno']
                        if Add['bnm']: FullAdd += (', ' if Add['bno'] else '') + Add['bnm']
                        if Add['st']: FullAdd += (', ' if Add['bnm'] else '') + Add['st']
                        if Add['loc']: FullAdd += (', ' if Add['st'] else '') + Add['loc']
                        if Add['city']: FullAdd += (', ' if Add['loc'] else '') + Add['city']
                        if Add['dst']: FullAdd += (', ' if Add['city'] else '') + Add['dst']
                        if Add['stcd']: FullAdd += (', ' if Add['dst'] else '') + Add['stcd']
                        if Add['pncd']: FullAdd += (', ' if Add['stcd'] else '') + Add['pncd']

                    request.env['bs.gst'].sudo().create({'api_response':res, 'registered_address':FullAdd,
                                                         'legal_name':LegalName, 'trade_name':TradeName,
                                                         'name': GSTIN, 'pan':GSTIN[2:12],'pincode':Pincode,
                                                         'reg_date':datetime.strptime(GSTReg, '%d/%m/%Y'),
                                                         'gst_updated_date':datetime.strptime(GSTLastUpdated, '%d/%m/%Y'),
                                                         'gst_status':'active' if GSTStatus == 'Active' else 'inactive',
                                                         'city':City, 'state_id':StateID, 'district_id':DistrictID })
                    return {'reg_add': FullAdd, 'trade_name': TradeName, 'legal_name': LegalName, 'city': City,
                            'district': DistrictID, 'state': StateID, 'pincode': Pincode}
                else: return False

            elif GSTExists: #if system has already captured GST information before
                return {'reg_add': GSTExists.registered_address, 'trade_name': GSTExists.trade_name,
                        'legal_name': GSTExists.legal_name, 'district': GSTExists.district_id.id,
                        'city': GSTExists.city, 'state': GSTExists.state_id.id, 'pincode': GSTExists.pincode}
            else:
                return False
        else: return False


