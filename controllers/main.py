from odoo import http
from odoo.http import request
from odoo.addons.account.controllers.terms import TermsController


class BSMainController(http.Controller):

    @http.route('/click/upload', type="http", auth="user", website=True)
    def bs_click_upload(self):
        return request.render('buildmart.bs_click_upload')

    @http.route('/price/enquiry', type="http", auth="user", website=True)
    def bs_price_enquiry(self):
        Partner = request.env.user.partner_id
        States = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'IN')])
        Categories = request.env['product.public.category'].sudo().search([('parent_id', '=', False),
                                                                           ('customer_type', 'in',
                                                                            [Partner.customer_type, 'both'])])
        Subcategories = request.env['product.public.category'].sudo().search([('parent_id', '!=', False),
                                                                              ('customer_type', 'in',
                                                                               [Partner.customer_type, 'both'])])
        Brands = request.env['product.attribute.value'].sudo().search(
            [('attribute_id', '=', request.env.ref('buildmart.brand_attribute').id),
             ('customer_type', 'in', [Partner.customer_type, 'both'])])
        UOM = request.env['uom.uom'].sudo().search([])
        values = {'states': States,
                  'categories': Categories,
                  'subcategories': Subcategories,
                  'brands': Brands,
                  'uoms': UOM}
        return request.render('buildmart.bs_price_enquiry_template', values)

    @http.route('/create/enquiry', type='json', auth="user", sitemap=False, website=True)
    def create_bs_enquiry(self, **kw):
        if kw.get('type') == 'PriceEnquiry':
            kw.pop('type')
            FinalVals = {}
            for i in kw:
                if type(kw[i]) == list:
                    FinalVals[i] = [(6, 0, list(map(int, kw[i])))]
                else:
                    FinalVals[i] = kw[i]
            EnqID = request.env['bs.enquiry'].sudo().create(FinalVals)
            return True if EnqID else False

        elif kw.get('type') == 'ClickUpload':
            EnquiryIDs = []
            DeliveryIDs = []
            if kw.get('cameras',False):
                for attach in kw.get('cameras'):
                    EnquiryIDs += [request.env['ir.attachment.enquiry'].sudo().create({'enquiry_filename': attach,
                                                                               'enquiry_file':
                                                                                   kw.get('cameras').get(attach).split(
                                                                                       ';base64,')[-1]}).id]
            if kw.get('audios',False):
                for attach in kw.get('audios'):
                    EnquiryIDs += [request.env['ir.attachment.enquiry'].sudo().create({'audio_file': kw.get('audios').get(attach)}).id]
            if kw.get('documents',False):
                for attach in kw.get('documents'):
                    EnquiryIDs += [request.env['ir.attachment.enquiry'].sudo().create({'enquiry_filename': attach,
                                                                               'enquiry_file':
                                                                                   kw.get('documents').get(attach).split(
                                                                                       ';base64,')[-1]}).id]
            # for attach in kw.get('delivery'):
            #     DeliveryIDs += [request.env['ir.attachment'].sudo().create({'type': 'binary', 'name': attach,
                                                                            # 'datas':
                                                                            #     kw.get('delivery').get(attach).split(
                                                                            #         ';base64,')[-1]}).id]
                                                                                

            
            ClickUpload = request.env['bs.click.upload'].sudo().create(
                {'price_enquiry_attachment_ids': [(6, 0, EnquiryIDs)],
                 # 'delivery_address_attachment_ids': [(6, 0, DeliveryIDs)],
                 'name': kw.get('name', "").strip(),
                 'phone_no': kw.get('phone', "").strip(),
                 'alt_phone_no': kw.get('alt_phone_no', "").strip(),
                 'gstin': kw.get('gstin').strip() if kw.get('gstin', False) else '',
                 'material': kw.get('material').strip() if kw.get('material', False) else '',
                 'material_type': kw.get('material_type').strip() if kw.get('material_type', False) else '',
                 'partner_id': request.env.user.partner_id.id,
                 'trade_name': kw.get('trade_name').strip() if kw.get('trade_name', False) else '',
                 'address': kw.get('address').strip()
                })
            return {'success':True} if ClickUpload else {'success':False}

        else:
            return {'success':False}

    @http.route('/policy/privacy', type="http", auth="public", website=True)
    def bs_policies(self):
        return request.render('buildmart.bs_privacy_policy')

    @http.route('/contactus', type="http", auth="public", website=True, sitemap=True)
    def bs_contactus(self):
        return request.render('buildmart.bs_contactus')

    @http.route('/bs/contactus', type="json", auth="public", website=True, sitemap=False)
    def bs_contactus_submit(self, **kw):
        try:
            return request.env['crm.lead'].sudo().create(kw)
        except Exception as e:
            print(e)
            return False

    @http.route(['/categories', '/categories/<string:cattype>'], type="http", auth="public", website=True)
    def all_categories(self, cattype=''):
        values = {'type': cattype}
        return request.render('buildmart.bs_all_categs', values)

    @http.route('/services', type="http", auth="public", website=True)
    def services(self):
        return request.render('buildmart.coming_soon', {'message': 'For Services, please contact'})

    @http.route('/sell', type="http", auth="public", website=True)
    def sell_with_us(self):
        return request.render('buildmart.coming_soon')

    @http.route('/faq', type="http", auth="public", website=True)
    def bs_faqs(self):
        return request.render('buildmart.coming_soon')

    @http.route('/notifications', type="http", auth="user", website=True, sitemap=True)
    def bs_notifications(self):
        Partner = request.env.user.partner_id
        Notifications = request.env['bs.notification'].sudo().search([('partner_id', '=', Partner.id),('read','=',False)])
        return request.render('buildmart.bs_notifications', {'notifications': Notifications})

    @http.route(['/brands/<string:alphabet>'], type="http", auth="public", website=True, sitemap=False)
    def return_brands(self, alphabet='a'):
        PartnerCustType = request.env.user.partner_id.customer_type if request.env.user else False
        if alphabet:
            Brands = request.env['product.attribute.value'].sudo().search([('name', '=ilike', alphabet + '%'),
                                           ('customer_type', 'in', ['both', PartnerCustType]),
                                           ('attribute_id', '=', request.env.ref('buildmart.brand_attribute').id)])
        return request.render('buildmart.brands_page', {'brands': Brands, 'are_top_brands': False})

    @http.route(['/brands'], type="http", auth="public", website=True, sitemap=True)
    def return_brands(self, ):
        PartnerCustType = request.env.user.partner_id.customer_type if request.env.user else False
        Brands = request.env['product.attribute.value'].sudo().search([
            ('customer_type', 'in', ['both', PartnerCustType]),
            ('attribute_id', '=', request.env.ref('buildmart.brand_attribute').id)])
        return request.render('buildmart.brands_page', {'brands': Brands, 'are_top_brands': False})

    @http.route(['/topbrands',
                 '/topbrands/<int:category>'], type="http", auth="public", website=True)
    def return_topbrands(self, category=False, **post):
        PartnerCustType = request.env.user.partner_id.customer_type if request.env.user else False
        Brands = request.env['product.attribute.value'].sudo().search(
            [('attribute_id', '=', request.env.ref('buildmart.brand_attribute').id),
             ('customer_type', 'in', ['both', PartnerCustType]),
             ('is_top_brand', '=', True)])
        return request.render('buildmart.brands_page', {'brands': Brands, 'are_top_brands': True})

    @http.route('/upload/enquiry', type="http", auth="user", website=True)
    def click_and_upload(self, **kw):
        return request.render('buildmart.bs_click_upload')

class BSTermsController(TermsController):

    @http.route('/terms', type='http', auth='public', website=True, sitemap=True)
    def bs_terms_conditions(self):
        return request.render("buildmart.bs_terms")
