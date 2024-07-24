from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.http import request
try:
    from urllib.request import urlopen
except ImportError:
    from urllib3 import urlopen

from odoo import models, fields, api, _
from odoo.addons.http_routing.models.ir_http import slug
import logging
_logger = logging.getLogger(__name__)

class BSHomepageBackend(models.Model):
    _name = "bs.homepage"
    _rec_name = 'website_id'

    footer_link_ids = fields.One2many('bs.footer.links', 'footer_link_id', string='Footer Links')
    header_search_ids = fields.One2many('bs.header.search', 'header_search_id', string="Header Search")

    company_id = fields.Many2one('res.company', 'Company')
    website_id = fields.Many2one('website', string='Website')

    # homepage
    banner_ids = fields.One2many('banner.image', 'banner_id', string='Banners')
    client_review_ids = fields.One2many('bs.client.review', 'review_id', string="Client Reviews")
    our_seller_ids = fields.One2many('bs.homepage.sellers', 'seller_id', string="Our Sellers")
    our_brand_ids = fields.One2many('bs.homepage.brands', 'our_brand_id', string="Our Brands")

    hot_deals_label = fields.Char('Hot Deals Label')
    hot_deal_ids = fields.One2many('bs.homepage.products', 'hot_deal_id', string="Hot Deals")

    best_selling_label = fields.Char('Best Selling Label')
    best_selling_ids = fields.One2many('bs.homepage.products', 'best_selling_id', string="Best Selling Products")

    trending_product_label = fields.Char('Trending Products Label')
    trending_product_ids = fields.One2many('bs.homepage.products', 'trending_prod_id',
                                           string="Trending Products of Week")

    top_blocks_label = fields.Char('Top Blocks Label')
    top_block_ids = fields.One2many('bs.homepage.products', 'top_block_id', string="Top Selling Blocks")

    cement_brand_label = fields.Char('Cement Brands Label')
    cement_brand_ids = fields.One2many('bs.homepage.brands', 'cement_brand_id', string="Top Cement Brands")

    safety_brand_label = fields.Char('Safety Brands Label')
    safety_brand_ids = fields.One2many('bs.homepage.brands', 'safety_brand_id', string="Top Safety Brands")

    steel_brand_label = fields.Char('Steel Brands Label')
    steel_brand_ids = fields.One2many('bs.homepage.brands', 'steel_brand_id', string="Top Steel Brands")

    block_brand_label = fields.Char('Block Brands Label')
    block_brand_ids = fields.One2many('bs.homepage.brands', 'block_brand_id', string="Top Blocks Brands")

    top_category_ids = fields.One2many('bs.homepage.categories', 'top_categ_id', string="Top Categories")

    safety_category_label = fields.Char('Safety Categories Label')
    safety_category_ids = fields.One2many('bs.homepage.categories', 'safety_categ_id', string="Top Safety Categories")

    def get_cdn_url(self, brand):
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


class BSFooterLinks(models.Model):
    _name = 'bs.footer.links'
    _description = 'Footer Links'

    name = fields.Char('Label')
    page_url = fields.Char('Redirecting URL')
    link_ids = fields.One2many('bs.footer.sublinks','footer_link_id','Links')
    footer_link_id = fields.Many2one('bs.homepage')

class BSFooterSubLinks(models.Model):
    _name = 'bs.footer.sublinks'
    _description = 'Footer Sublinks'
    _order = "sequence"

    name = fields.Char('Name')
    page_url = fields.Char('Redirecting URL')
    sequence = fields.Integer('Sequence', help="Sequence used to order Links for Footer")
    footer_link_id = fields.Many2one('bs.footer.links')


class BSBannerImages(models.Model):
    _name = 'banner.image'
    _description = 'Banner Images'
    _inherit = 'image.mixin'

    name = fields.Char(string='Description', help="Description of banner.")
    color = fields.Char(string='Hex Color Code', help='Homepage Background Color')
    redirecting_url = fields.Char('Redirecting URL', help="URL to redirect to")
    banner_id = fields.Many2one('bs.homepage')
    ecomm_id = fields.Many2one('product.public.category')
    banner_content = fields.Html('Banner Content')
    s3_url = fields.Char('S3 Bucket URL', help="To get image from s3 bucket")

class BSHeaderSearch(models.Model):
    _name = "bs.header.search"
    _description = 'Header Search'
    _order = "sequence"

    name = fields.Char(string="Search Label")
    sequence = fields.Integer('Sequence', help="Sequence used to order header search")
    categ_ids = fields.Many2many('product.public.category','header_search_rel','categ_id','search_id', string="Categories")
    header_search_id = fields.Many2one('bs.homepage')

class BSClientReviews(models.Model):
    _name = "bs.client.review"
    _description = 'Client Review'
    _order = "sequence"

    name = fields.Char('Review Title')
    client_id = fields.Many2one('res.partner', string="Client")
    sequence = fields.Integer('Sequence', help="Sequence in which to show reviews")
    review = fields.Text('Review')
    review_id = fields.Many2one('bs.homepage')


class BSHomepageSellers(models.Model):
    _name = "bs.homepage.sellers"
    _rec_name = "partner_id"
    _order = "sequence"

    partner_id = fields.Many2one('res.partner')
    sequence = fields.Integer('Sequence')
    seller_id = fields.Many2one('bs.homepage')
    image = fields.Image("Image", max_width=128, max_height=128)


class BSHomepageBrands(models.Model):
    _name = "bs.homepage.brands"
    _rec_name = "brand_id"
    _order = "sequence"

    label = fields.Char('Label')
    brand_id = fields.Many2one('product.attribute.value')
    sequence = fields.Integer('Sequence')
    our_brand_id = fields.Many2one('bs.homepage')
    cement_brand_id = fields.Many2one('bs.homepage')
    safety_brand_id = fields.Many2one('bs.homepage')
    steel_brand_id = fields.Many2one('bs.homepage')
    block_brand_id = fields.Many2one('bs.homepage')
    image = fields.Image("Image")
    s3_url = fields.Char('S3 Bucket URL', help="To get image from s3 bucket")



class BSHomepageProducts(models.Model):
    _name = "bs.homepage.products"
    _rec_name = "product_id"
    _order = "sequence"

    label = fields.Char('Label')
    product_id = fields.Many2one('product.template')
    sequence = fields.Integer('Sequence')
    hot_deal_id = fields.Many2one('bs.homepage')
    best_selling_id = fields.Many2one('bs.homepage')
    trending_prod_id = fields.Many2one('bs.homepage')
    top_block_id = fields.Many2one('bs.homepage')
    image = fields.Image("Image", max_width=128, max_height=128)
    s3_url = fields.Char('S3 Bucket URL', help="To get image from s3 bucket")


class BSHomepageCategories(models.Model):
    _name = "bs.homepage.categories"
    _rec_name = "category_id"
    _order = "sequence"

    label = fields.Char('Label')
    category_id = fields.Many2one('product.public.category')
    sequence = fields.Integer('Sequence')
    top_categ_id = fields.Many2one('bs.homepage')
    safety_categ_id = fields.Many2one('bs.homepage')
    image = fields.Image("Image", max_width=128, max_height=128)
    s3_url = fields.Char('S3 Bucket URL', help="To get image from s3 bucket")
