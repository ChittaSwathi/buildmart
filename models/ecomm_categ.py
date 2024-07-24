from odoo import api, fields, models
from odoo.http import request
try:
    from urllib.request import urlopen
except ImportError:
    from urllib3 import urlopen
from odoo import models, fields, api, _
from odoo.addons.http_routing.models.ir_http import slug
import logging
_logger = logging.getLogger(__name__)


class BSEcommCategories(models.Model):
    _inherit = "product.public.category"

    def get_redirect_url(self, products, product):
        for k, v in products.items():
            if v == product:
                return self.env['product.template'].browse(int(k))
        return False

    def get_sorted_brand(self, products):
        ProdVariants = products.mapped('attribute_line_ids').filtered(
            lambda x: x.attribute_id.id == self.env.ref('buildmart.brand_attribute').id)
        sortedBrand = ProdVariants.mapped('value_ids').sorted(lambda x: x.position)
        return sortedBrand

    def get_recursive_url(self, URL="/"):
        if self.parent_id:
            URL = self.parent_id.get_recursive_url(URL) + '/' + slug(self)
        else:
            if URL == '/':
                URL += slug(self)
            else:
                URL += slug(self)
        return URL

    def get_cdn_url_brand(self, brand):
        final_uri_preview = "/web/static/img/placeholder.png"
        try:
            from werkzeug import urls
            import requests
            s3 = ['brand']
            Website_env = self.env['website']
            website = Website_env.get_current_website()
            cdn_url = website.cdn_url
            if cdn_url:
                s3.append(slug(brand))
                uri = '/'.join(s3)
                final_uri = urls.url_join(cdn_url, uri)
                response = requests.get(final_uri)
                if response.status_code != 200:
                    homepage = self.env['bs.homepage'].search([], limit=1)
                    return final_uri_preview
                return final_uri
            else:
                return final_uri_preview
        except:
            pass
        return final_uri_preview

    def get_cdn_url(self, URL="/"):
        final_uri_preview = "/web/static/img/placeholder.png"
        try:
            from werkzeug import urls
            import requests
            s3 = ['category']

            Website_env = self.env['website']
            website = Website_env.get_current_website()
            cdn_url = website.cdn_url
            if self.s3_url:
                return self.s3_url
            # if cdn_url:
            #     s3.append(slug(self))
            #     uri = '/'.join(s3)
            #     final_uri = urls.url_join(cdn_url, uri)
            #     response = requests.get(final_uri)
            #     if response.status_code != 200:
            #         homepage = self.env['bs.homepage'].search([], limit=1)
            #         return final_uri_preview
            #     return final_uri
            else:
                return final_uri_preview
        except:
            pass
        return final_uri_preview

    def _domain_brands(self):
        return [('attribute_id', '=', self.env.ref('buildmart.brand_attribute').id)]

    @api.depends('create_date', 'write_date', 'name')
    def _compute_slug(self):
        for categ in self:
            if categ.id: categ.update({'category_slug': slug(categ)})

    categ_type_ids = fields.Many2many('ecomm.categ.type', 'ecomm_categ_type_rel', 'categ_id', 'type_id', string='Type')
    banner_ids = fields.One2many('banner.image', 'ecomm_id', string='Banners')
    banner_s3_url = fields.One2many('banner.image.s3', 'ecomm_id', string='Banners')

    # Used in Header search/megamenu, l1 listing page (Category specific page)
    top_brand_ids = fields.Many2many('product.attribute.value', 'ecomm_top_brand_rel', 'ecomm_id', 'brand_id',
                                     string="Top Brands",
                                     domain=_domain_brands)
    top_vendor_ids = fields.Many2many('res.partner', 'ecomm_top_vendor_rel', 'ecomm_id', 'vendor_id',
                                      string="Top Vendors",
                                      domain=[('supplier_rank', '>', 0)])
    specification_ids = fields.One2many('product.template.attribute.line', 'ecomm_id', 'Specifications')
    search_id = fields.Many2one('res.company')
    pdp_template_id = fields.Many2one('ir.ui.view', string="View Template")
    is_coming_soon = fields.Boolean("Is coming soon?")
    upload_enq1_id = fields.Many2one('bs.enquiry')
    upload_enq2_id = fields.Many2one('bs.enquiry')

    allcategs_image = fields.Image("Image", max_width=128, max_height=128,
                                   help="This image will be displayed in all categories page like construction, industrial etc.")
    megamenu = fields.Boolean('Show in Megamenu', default=True)
    megamenu_sequence = fields.Integer('Megamenu Sequence', help="Sequence for displaying Megamenu in website.")

    products_description = fields.Html('Products Description')
    customer_type = fields.Selection([('b2b', 'B2B'),
                                      ('b2c', 'B2C'),
                                      ('both', 'Both')], string='Customer Type', default="both")
    l2_view = fields.Selection([('tile_view', 'Tile View'),
                                ('brand_view', 'Brands View'),
                                ('ecomm_view', 'eCommerce View')], string="L2 View")
    is_trending = fields.Boolean("Is Trending?")
    category_slug = fields.Char(string="Slug", copy=False, help="S3 bucket name same as Slug", compute='_compute_slug',
                                store=True)
    detailed_info = fields.Html('Category Information')
    s3_url = fields.Char('S3 Bucket URL', help="To get image from s3 bucket")

    @api.onchange('products_description')
    def _onchange_products_description(self):
        if self.id and self.products_description:
            self.env['product.template'].search([('public_categ_ids', 'child_of', [self._origin.id]),
                                                 ('website_description', 'in',
                                                  ['<p><br></p>', '<p><br> </p>', '<p><br /></p >'])]). \
                write({'website_description': self.products_description})

    def get_brands(self, eCommCategIDs):
        ProductIDs, Brands = [], []
        for categ in eCommCategIDs:
            ProductIDs += self.env['product.template'].search(['|', ('public_categ_ids', 'child_of', int(categ)),
                                                               ('public_categ_ids', '=', int(categ))]).ids
            Brands += self.env['product.template.attribute.line'].search(
                [('attribute_id', '=', self.env.ref('buildmart.brand_attribute').id),
                 ('product_tmpl_id', 'in', ProductIDs)]).mapped('value_ids')
        return self.env['product.attribute.value'].browse(
            list(set([brand.ids if len(brand) > 1 else brand.id for brand in Brands])))


class BSEcommCategs3(models.Model):
    _name = "banner.image.s3"
    _description = 'Ecommerce Category s3 url link'

    name = fields.Char('Name')
    ecomm_id = fields.Many2one('product.public.category')


class BSEcommCategType(models.Model):
    _name = "ecomm.categ.type"
    _description = 'Ecommerce Category Type'

    name = fields.Char('Name', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Category type already exists !"),
    ]


class BSGenericPromotions(models.Model):
    _name = "bs.generic.promotion"
    _description = "Generic Promotions"

    content = fields.Text('Content')
    s3_image_url = fields.Char('Banner Image')
    image_redirection_url = fields.Char('Image Redirection')
