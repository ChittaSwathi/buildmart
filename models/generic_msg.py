from odoo import fields, models, _
import requests
import json
import logging
_logger = logging.getLogger(__name__)

class BSGenericWhatsappMessages(models.Model):
    _name = 'bs.generic.whatsapp.msg'
    _description = "Generic Whatsapp Messages"

    mobile = fields.Char('Mobile Number(s)')
    message = fields.Html('Message')

    def action_send_message(self):
        param = self.env['res.config.settings'].sudo().get_values()
        no_phone_partners = []
        whatsapp_number = '+91 9059364704'
        message = 'test hey this is swathi'
        whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+91', "")
        phone_exists_url = param.get('whatsapp_endpoint') + '/checkPhone?token=' + param.get(
            'whatsapp_token') + '&phone=91' + whatsapp_msg_number_without_code
        phone_exists_response = requests.get(phone_exists_url)
        json_response_phone_exists = json.loads(phone_exists_response.text)

        if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and \
                json_response_phone_exists['result'] == 'exists':
            url = param.get('whatsapp_endpoint') + '/sendMessage?token=' + param.get('whatsapp_token')
            headers = {"Content-Type": "application/json"}
            tmp_dict = {
                "phone": "+91" + whatsapp_msg_number_without_code,
                "body": str(message)
            }
            response = requests.post(url, json.dumps(tmp_dict), headers=headers)
            if response.status_code == 201 or response.status_code == 200:
                _logger.info("\nSend Message successfully")
                # self.write({'state': 'done'})
