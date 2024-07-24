from odoo import http, _
from odoo.http import request
import requests
import json
import datetime
from datetime import datetime
import re
from odoo.addons.web.controllers.main import ReportController
from odoo.addons.web.controllers.main import _serialize_exception
from odoo.tools import html_escape
from odoo.tools.safe_eval import safe_eval, time
from odoo.http import content_disposition, request
from odoo.exceptions import ValidationError, UserError, RedirectWarning
from odoo.addons.account_reports.controllers.main import FinancialReportController
import logging
_logger = logging.getLogger(__name__)

class BSReportController(ReportController):

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, context=None):
        requestcontent = json.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        reportname = '???'
        try:
            if type in ['qweb-pdf', 'qweb-text']:
                converter = 'pdf' if type == 'qweb-pdf' else 'text'
                extension = 'pdf' if type == 'qweb-pdf' else 'txt'

                pattern = '/report/pdf/' if type == 'qweb-pdf' else '/report/text/'
                reportname = url.split(pattern)[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter=converter, context=context)
                else:
                    # Particular report:
                    data = dict(url_decode(url.split('?')[1]).items())  # decoding the args represented in JSON
                    if 'context' in data:
                        context, data_context = json.loads(context or '{}'), json.loads(data.pop('context'))
                        context = json.dumps({**context, **data_context})
                    response = self.report_routes(reportname, converter=converter, context=context, **data)

                report = request.env['ir.actions.report']._get_report_from_name(reportname)
                filename = "%s.%s" % (report.name, extension)

                if docids:
                    ids = [int(x) for x in docids.split(",")]
                    obj = request.env[report.model].browse(ids)

                    if report.model in ('account.move', 'sale.order', 'purchase.order', 'stock.picking') and not obj.authorized_by:
                        if report.model == 'account.move':
                            ReportType = 'Invoice' if obj.move_type=='out_invoice' else 'Bill'
                        else:
                            ReportType = 'Order'
                        raise UserError(_('%s needs to be Verified to proceed further.'%(ReportType)))

                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                response.headers.add('Content-Disposition', content_disposition(filename))
                return response
            else:
                return
        except Exception as e:
            _logger.exception("Error while generating report %s", reportname)
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))

class FinancialReportController(FinancialReportController):

    @http.route('/account_reports', type='http', auth='user', methods=['POST'], csrf=False)
    def get_report(self, model, options, output_format, financial_id=None, **kw):
        uid = request.session.uid
        account_report_model = request.env['account.report']
        options = json.loads(options)
        cids = kw.get('allowed_company_ids')
        if not cids or cids == 'null':
            cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        allowed_company_ids = [int(cid) for cid in cids.split(',')]
        report_obj = request.env[model].with_user(uid).with_context(allowed_company_ids=allowed_company_ids)
        if financial_id and financial_id != 'null':
            report_obj = report_obj.browse(int(financial_id))
        report_name = report_obj.get_report_filename(options)
        if report_name == 'partner_ledger':
            print(options['partner_ids'])
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('xlsx')),
                        ('Content-Disposition', content_disposition(report_name + '.xlsx'))
                    ]
                )
                response.stream.write(report_obj.get_xlsx(options))
            if output_format == 'pdf':
                response = request.make_response(
                    report_obj.get_pdf(options),
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('pdf')),
                        ('Content-Disposition', content_disposition(report_name + '.pdf'))
                    ]
                )
            if output_format == 'xml':
                content = report_obj.get_xml(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('xml')),
                        ('Content-Disposition', content_disposition(report_name + '.xml')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'xaf':
                content = report_obj.get_xaf(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('xaf')),
                        ('Content-Disposition', content_disposition(report_name + '.xaf')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'txt':
                content = report_obj.get_txt(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('txt')),
                        ('Content-Disposition', content_disposition(report_name + '.txt')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'csv':
                content = report_obj.get_csv(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('csv')),
                        ('Content-Disposition', content_disposition(report_name + '.csv')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'kvr':
                content = report_obj._get_kvr(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('txt')),
                        ('Content-Disposition', content_disposition(report_name + '.kvr')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'zip':
                content = report_obj._get_zip(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('zip')),
                        ('Content-Disposition', content_disposition(report_name + '.zip')),
                    ]
                )
                # Adding direct_passthrough to the response and giving it a file
                # as content means that we will stream the content of the file to the user
                # Which will prevent having the whole file in memory
                response.direct_passthrough = True
            return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))