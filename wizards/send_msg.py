from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
from odoo.tools.safe_eval import safe_eval, time

class SendWAMessage(models.TransientModel):
    _inherit = 'whatsapp.msg'
    
    
    @api.model
    def default_get(self, fields):
        result = super(SendWAMessage, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        res_id = self.env.context.get('active_id')
        rec = self.env[active_model].browse(res_id)
        rec = rec.with_context(lang=rec.partner_id.lang)
        self = self.with_context(lang=rec.partner_id.lang)
        Attachment = self.env['ir.attachment']
        res_name = ''
        if active_model == 'account.move':
            if rec.name:
                res_name = 'Invoice_' + rec.name.replace('/', '_') if active_model == 'account.move' else rec.name.replace('/', '_')
        msg = result.get('message', '')
        result['message'] = msg
        res_user_id = self.env['res.users'].search([('partner_id', '=', rec.partner_id.id)])
        if not self.env.context.get('default_recipients') and active_model and hasattr(self.env[active_model], '_sms_get_default_partners'):
            model = self.env[active_model]
            records = self._get_records(model)
            partners = records._sms_get_default_partners()
            phone_numbers = []
            no_phone_partners = []
            self = self.with_context(lang=rec.partner_id.lang)
            if active_model == 'sale.order':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    # doc_name = 'quotation' if rec.state in ('approved', 'to_confirm') else 'order'
                    doc_name = _("order")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_order_info_msg'):
                        msg += "\n\n " + _("Your") + " "
                        if self.env.context.get('proforma'):
                            msg += _("in attachment your pro-forma invoice")
                        else:
                            msg += doc_name + " *" + rec.name + "* "
                        if rec.origin:
                            msg += _("(with reference") + " : " + rec.origin + ")"
                        msg += _(" is placed")
                        msg += "\n" + _("Total Amount") + ": " + self.format_amount(rec.amount_total, rec.pricelist_id.currency_id)
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_order_product_details_msg'):
                        msg += "\n\n" + _("Following is your order details.")
                        for line_id in rec.order_line:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.product_uom_qty and line_id.product_uom.name:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                                if line_id.price_unit:
                                    msg += "\n*" + _("Unit Price") + ":* " + str(line_id.price_unit)
                                if line_id.price_subtotal:
                                    msg += "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                            msg += "\n------------------"
                    msg += "\n" + _("Please find attached sale order which will help you to get detailed information.")
                    # if rec
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature

                    report_obj = self.env.ref('sale.action_report_saleorder')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'sale.order',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'account.move':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    doc_name = _("invoice")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_info_msg'):
                        msg += "\n\n" + _("Here is your ")
                        if rec.state == 'draft':
                            msg += doc_name + " *" + _("draft invoice") + "* "
                        else:
                            msg += doc_name + " *" + rec.name + "* "
                        msg += "\n" + _("Total Amount") + ": " + self.format_amount(rec.amount_total, rec.currency_id)
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_product_details_msg'):
                        msg += "\n\n" + _("Following is your order details.")
                        for line_id in rec.invoice_line_ids:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.quantity:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.quantity)
                                if line_id.price_unit:
                                    msg += "\n*" + _("Unit Price") + ":* " + str(line_id.price_unit)
                                if line_id.price_subtotal:
                                    msg += "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                            msg += "\n------------------"

                    msg += "\n" + _("Please find attached invoice which will help you to get detailed information.")
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_invoice_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature
#                     report_obj = self.env.ref('account.account_invoices_without_payment')
                    report_obj = self.env.ref('account.account_invoices')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'account.move',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'stock.picking':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    # doc_name = 'stock picking' if rec.state in ('assigned', 'done') else 'picking'
                    doc_name = _("Delivery order")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_stock_info_msg'):
                        msg += "\n\n" + _("Here is your") + " "
                        msg += doc_name + " *" + rec.name + "* "
                        if rec.origin:
                            msg += "(" + _("with reference") + ": " + rec.origin + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_stock_product_details_msg'):
                        msg += "\n\n" + _("Following is your delivery order details.")
                        for line_id in rec.move_ids_without_package:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.product_uom_qty and line_id.product_uom:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                                # if line_id.quantity_done:
                                #     msg += "\n*" + _("Done") + ":* "+str(line_id.quantity_done)
                            msg += "\n------------------"
                    msg += "\n" + _("Please find attached delivery order which will help you to get detailed information.")
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_stock_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature

                    report_obj = self.env.ref('stock.action_report_picking')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'stock.picking',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'purchase.order':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    doc_name = _("Purchase order")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_purchase_order_info_msg'):
                        msg += "\n\n" + _("Here is your") + " "
                        msg += doc_name + " *" + rec.name + "* "
                        if rec.origin:
                            msg += "(" + _("with reference") + ": " + rec.origin + ")"
                        msg += "\n" + _("Total Amount") + ": " + self.format_amount(rec.amount_total, rec.currency_id) + "."
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_purchase_order_product_details_msg'):
                        msg += "\n\n" + _("Following is your order details.")
                        for line_id in rec.order_line:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.product_qty and line_id.product_uom:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.product_qty) + " " + str(line_id.product_uom.name)
                                if line_id.price_unit:
                                    msg += "\n*" + _("Unit Price") + ":* " + str(line_id.price_unit)
                                if line_id.price_subtotal:
                                    msg += "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)

                            msg += "\n------------------"
                    msg += "\n " + _("Please find attached purchase order which will help you to get detailed information.")
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_purchase_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature


                    report_obj = self.env.ref('purchase.action_report_purchase_order')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'purchase.order',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'account.payment':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    doc_name = _("account payment")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_info_msg'):
                        msg += "\n\n" + _("Your") + " "
                        if rec.name:
                            msg += doc_name + " *" + rec.name + "* "
                        else:
                            msg += doc_name + " *" + _("Draft Payment") + "* "
                        msg += " " + _("with Total Amount") + " " + self.format_amount(rec.amount, rec.currency_id) + "."
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_product_details_msg'):
                        msg += "\n\n" + _("Following is your payment details.")
                        if rec:
                            if rec.payment_type:
                                msg += "\n\n*" + _("Payment Type") + ":* " + rec.payment_type
                            if rec.journal_id:
                                msg += "\n*" + _("Payment Journal") + ":* " + rec.journal_id.name
                            if rec.date:
                                msg += "\n*" + _("Payment date") + ":* " + str(rec.date)
                            if rec.ref:
                                msg += "\n*" + _("Memo") + ":* " + str(rec.ref)
                    msg += "\n " + _("Please find attached account payment which will help you to get detailed information.")
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_invoice_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature
                    attachment_ids = []
                    attachment_data = {}
                    # if rec.state == 'draft':


                    report_obj = self.env.ref('account.action_report_payment_receipt')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    if report_obj.print_report_name:
                        report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                        res = base64.b64encode(pdf[0])
                        attachments = []
                        attachments.append((filename, pdf))
                        attachment_ids = []

                        attachment_data = {
                            'name': filename,
                            'datas': res,
                            'type': 'binary',
                            'res_model': 'account.payment',
                            'res_id': rec.id,
                        }
                    else:
                        pdf = self.env.ref('account.action_report_payment_receipt').sudo()._render_qweb_pdf([rec.id])
                        res = base64.b64encode(pdf[0])
                        res_name = 'account.action_report_payment_receipt'
                        attachments = []
                        attachments.append((res_name, pdf))
                        attachment_ids = []
                        attachment_data = {
                            'name': 'Payment Receipt.pdf',
                            'datas': res,
                            'type': 'binary',
                            'res_model': 'account.payment',
                            'res_id': rec.id,
                        }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))
            result['message'] = msg
            for partner in partners:
                number = self._msg_sanitization(partner, self.env.context.get('field_name') or 'mobile')
                if number:
                    phone_numbers.append(number)
                else:
                    no_phone_partners.append(partner.name)
            if len(partners) > 1:
                if no_phone_partners:
                    raise UserError(_('Missing mobile number for %s.') % ', '.join(no_phone_partners))
            result['partner_ids'] = [(6, 0, partners.ids)]
            result['message'] = msg
        return result