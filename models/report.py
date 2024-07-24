from odoo import api, fields, models, _
import datetime, io, xlsxwriter
from datetime import datetime
from babel.dates import format_date
import markupsafe

import logging
_logger = logging.getLogger(__name__)

try:
    from urllib.request import urlopen
except ImportError:
    from urllib3 import urlopen

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def _init_filter_partner(self, options, previous_options=None):
        if options.get('date') and options['date'].get('filter') == 'this_year_today':
            options['date']['date_to'] = datetime.today().strftime('%Y-%m-%d')

        if not self.filter_partner:
            return

        options['partner'] = True
        options['partner_ids'] = previous_options and previous_options.get('partner_ids') or []
        options['partner_categories'] = previous_options and previous_options.get('partner_categories') or []
        selected_partner_ids = [int(partner) for partner in options['partner_ids']]
        selected_partners = selected_partner_ids and self.env['res.partner'].browse(selected_partner_ids) or self.env['res.partner']
        options['selected_partners'] = selected_partners

        options['selected_partner_ids'] = selected_partners.mapped('name')
        selected_partner_category_ids = [int(category) for category in options['partner_categories']]
        selected_partner_categories = selected_partner_category_ids and self.env['res.partner.category'].browse(selected_partner_category_ids) or self.env['res.partner.category']
        options['selected_partner_categories'] = selected_partner_categories.mapped('name')

        CustAddress, CustVat, CustCode, CustType, CustContact, CustAcctsPOC, CustSalesPOC = '', '', '', '', '', '', ''
        if selected_partner_ids and len(selected_partner_ids)==1:
            SelectedPartner = self.env['res.partner'].browse(selected_partner_ids[0])
            if SelectedPartner:
                CustVat = SelectedPartner.vat
                CustCode = SelectedPartner.partner_code
                CustType = SelectedPartner.customer_type.upper() if SelectedPartner.customer_type else ''

                options['cust_contact'] = SelectedPartner.email or ''
                if SelectedPartner.mobile:
                    if options['cust_contact']:
                        options['cust_contact'] += ' / ' + SelectedPartner.mobile
                    else:
                        options['cust_contact'] += SelectedPartner.mobile

                CustAddress = SelectedPartner.name
                if SelectedPartner.user_id:
                    CustSalesPOC = SelectedPartner.user_id.email
                    if SelectedPartner.user_id.mobile:
                        if CustSalesPOC:
                            CustSalesPOC +=  ' / ' + SelectedPartner.user_id.mobile
                        else:
                            CustSalesPOC += SelectedPartner.user_id.mobile

                if SelectedPartner.sitename_id: CustAddress += ',' + SelectedPartner.sitename_id.name
                if SelectedPartner.street: CustAddress += ',' + SelectedPartner.street
                if SelectedPartner.street2: CustAddress += ',' + SelectedPartner.street2
                if SelectedPartner.city: CustAddress += ',' + SelectedPartner.city
                if SelectedPartner.landmark: CustAddress += ',' + SelectedPartner.landmark
                if SelectedPartner.district_id: CustAddress += ',' + SelectedPartner.district_id.name
                if SelectedPartner.state_id: CustAddress += ',' + SelectedPartner.state_id.name
                if SelectedPartner.zip: CustAddress += ',' + SelectedPartner.zip
                if SelectedPartner.country_id: CustAddress += ',' + SelectedPartner.country_id.name
        options['cust_address'] = CustAddress
        options['cust_vat'] = CustVat
        options['cust_code'] = CustCode
        options['cust_type'] = CustType
        options['cust_contact'] = CustContact
        options['cust_accts_poc'] = "accounts@buildmart.com / +91 96424 96424"
        options['cust_sales_poc'] = CustSalesPOC
        options['report_name'] = self._name
        options['sitename'] = False
        
    #override
    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
       
        site_name = options.get('sitename', False) if options else False
        options = self._get_options(options)
        self = self.with_context(self._set_context(options)) # For multicompany, when allowed companies are changed by options (such as aggregare_tax_unit)
        options['sitename'] = site_name
        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic
        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts']]
        if options.get('analytic_tags') is not None:
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in options['analytic_tags']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for category in (options.get('partner_categories') or [])]

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break

        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(options),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view']._render_template(self._get_templates().get('search_template', 'account_report.search_template'), values=searchview_dict),
                }
        return info
    
    
    # @api.model
    # def _format_aml_name(self, line_name, move_ref, move_name=None):
    #     names = []
    #     if move_name is not None and move_name != '/':
    #         names.append(move_name)
    #     if move_ref and move_ref != '/':
    #         names.append(move_ref)
    #     if self._name != 'account.partner.ledger':
    #         if line_name and line_name != move_name and line_name != '/':
    #             names.append(line_name)
    #     name = '-'.join(names)
    #     return name

    def get_html(self, options, line_id=None, additional_context=None):
        self = self.with_context(self._set_context(options))
        ledger_type = self.env.context.get('ledger_type', False)
        templates = self._get_templates()
        report_manager = self._get_report_manager(options)

        render_values = {
            'report': {
                'name': self._get_report_name(),
                'summary': report_manager.summary,
                'company_name': self.env.company.name,
            },
            'options': options,
            'context': self.env.context,
            'model': self,
        }
        if additional_context:
            render_values.update(additional_context)

        # Create lines/headers.
        if line_id:
            headers = options['headers']
            lines = self._get_lines(options, line_id=line_id)
            template = templates['line_template']
        else:
            headers, lines = self._get_table(options)
            if ledger_type == 'bs':
                headers = [
                    [
                        {},
                        {'name': 'Date', 'class': 'date'},
                        {'name': 'JRNL'},
                        {'name': 'Account'},
                        {'name': 'Invoice/ Payment  Ref Number'},
                        {'name': 'Item Description'},
                        {'name': 'Total Qty'},
                        {'name': 'Customer Ref/ PO'},
                        {'name': 'Site Name'},
                        {'name': 'Delivery Location'},
                        {'name': 'Vehicle Number'},
                        {'name': 'Matching Number'},
                        {'name': 'Payment Terms'},
                        {'name': 'Amount Due', 'class': 'number'},
                        {'name': 'Due Date', 'class': 'date'},
                        {'name': 'Date of Payment', 'class': 'date'},
                        {'name': 'Delay Days'},
                        {'name': 'Initial Balance', 'class': 'number'},
                        {'name': 'Debit', 'class': 'number'},
                        {'name': 'Credit', 'class': 'number'},
                        {'name': 'Closing Balance', 'class': 'number'}
                    ]
                ]
            options['headers'] = headers
            template = templates['main_template']
        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)
        if ledger_type == 'bs':
            for line in lines:
                if "colspan" in line:
                    line['columns'] = [
                                          {'name': ''},
                                          {'name': ''},
                                          {'name': ''},
                                          {'name': ''},
                                          {'name': ''},
                                          {'name': ''},
                                          {'name': ''},
                                          {'name': ''},
                                          {'name': ''},
                                          {'name': ''},
                                          {'name': ''}] + line.get('columns')
        render_values['lines'] = {'columns_header': headers, 'lines': lines}

        # Manage footnotes.
        footnotes_to_render = []
        if self.env.context.get('print_mode', False):
            footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
            number = 0
            for line in lines:
                f = footnotes.get(str(line.get('id')))
                if f:
                    number += 1
                    line['footnote'] = str(number)
                    footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

        # Render.
        html = self.env.ref(template)._render(render_values)
        if self.env.context.get('print_mode', False):
            for k, v in self._replace_class().items():
                html = html.replace(k, v)
            # append footnote as well
            html = html.replace(markupsafe.Markup('<div class="js_account_report_footnotes"></div>'),
                                self.get_html_footnotes(footnotes_to_render))

        return html

    @api.model
    def download_xlsx(self, opt):
        to_display_sitename = opt.get('sitename', False)

        partner = self.env.user.partner_id
        part = 'partner_' + str(partner.id)
        df = opt.get('date_from')
        if df:
            cdf = datetime.strptime(df, '%Y-%m-%d').strftime('%d/%m/%Y')
        if not df:
            starting_day_of_current_year = datetime.now().date().replace(month=1, day=1)
            cdf = starting_day_of_current_year.strftime('%d/%m/%Y')
            df = starting_day_of_current_year.strftime('%Y-%m-%d')
        dt = opt.get('date_to')
        if dt:
            cdt = datetime.strptime(dt, '%Y-%m-%d').strftime('%d/%m/%Y')
        if not dt:
            ending_day_of_current_year = datetime.now().date().replace(month=12, day=31)
            cdt = ending_day_of_current_year.strftime('%d/%m/%Y')
            dt = ending_day_of_current_year.strftime('%Y-%m-%d')
        strn = 'From ' + str(cdf) + ' to  ' + str(cdt)
        headers = []
        headers += [{'name': 'Date', 'class': 'date'},
                    {'name': 'JRNL'},
                    {'name': 'Account'},
                    {'name': 'Invoice/ Payment  Ref Number'},
                    {'name': 'Item Description'},
                    {'name': 'Total Qty'},
                    {'name': 'Customer Ref/ PO'}]
        if to_display_sitename: headers += [{'name': 'Site Name'}]
        headers += [{'name': 'Delivery Location'},
                    {'name': 'Vehicle Number'},
                    {'name': 'Matching Number'},
                    {'name': 'Payment Terms'},
                    {'name': 'Amount Due', 'class': 'number'},
                    {'name': 'Due Date', 'class': 'date'},
                    {'name': 'Date of Payment', 'class': 'date'},
                    {'name': 'Delay Days'},
                    {'name': 'Initial Balance', 'class': 'number'},
                    {'name': 'Debit', 'class': 'number'},
                    {'name': 'Credit', 'class': 'number'},
                    {'name': 'Closing Balance', 'class': 'number'}]
        options = {
            'ledger_type': 'bs',
            'unfolded_lines': [part],
            'date': {
                'string': strn,
                'period_type': 'custom',
                'mode': 'range',
                'strict_range': False,
                'date_from': df,
                'date_to': dt,
                'filter': 'custom'},
            'account_type': [
                {'id': 'receivable', 'name': 'Receivable', 'selected': False},
                {'id': 'payable', 'name': 'Payable', 'selected': False}],
            'all_entries': False,
            'partner': True,
            'partner_ids': [partner.id],
            'partner_categories': [],
            'selected_partner_ids': [partner.name],
            'selected_partner_categories': [],
            'unfold_all': False,
            'unreconciled': False,
            'unposted_in_period': False,
            'headers': [headers]
        }
        x = self.with_context({'model': 'account.partner.ledger'}).print_xlsx(options)
        return x

    @api.model
    def download_pdf(self, opt):
        partner_id = self.env.user.partner_id.id
        open_part = 'partner_' + str(partner_id)
        df = opt.get('date_from')
        if df:
            cdf = datetime.strptime(df, '%Y-%m-%d').strftime('%d/%m/%Y')
        if not df:
            starting_day_of_current_year = datetime.now().date().replace(month=1, day=1)
            cdf = starting_day_of_current_year.strftime('%d/%m/%Y')
            df = starting_day_of_current_year.strftime('%Y-%m-%d')
        dt = opt.get('date_to')
        if dt:
            cdt = datetime.strptime(dt, '%Y-%m-%d').strftime('%d/%m/%Y')
        if not dt:
            ending_day_of_current_year = datetime.now().date().replace(month=12, day=31)
            cdt = ending_day_of_current_year.strftime('%d/%m/%Y')
            dt = ending_day_of_current_year.strftime('%Y-%m-%d')
        strn = 'From ' + str(cdf) + ' to  ' + str(cdt)
        options = {
            'unfolded_lines': [open_part],
            'date': {
                'string': strn,
                'period_type': 'custom',
                'mode': 'range',
                'strict_range': False,
                'date_from': df,
                'date_to': dt,
                'filter': 'custom'},
            'account_type': [
                {'id': 'receivable', 'name': 'Receivable', 'selected': False},
                {'id': 'payable', 'name': 'Payable', 'selected': False}],
            'all_entries': True,
            'partner': True,
            'partner_ids': [partner_id],
            'partner_categories': [],
            'selected_partner_ids': ['Administrator'],
            'selected_partner_categories': [],
            'unfold_all': False,
            'unreconciled': False,
            'unposted_in_period': False,
            'headers': [
                [{}, {'name': 'JRNL'}, {'name': 'Account'}, {'name': 'Ref'},
                 {'name': 'Due Date', 'class': 'date'},
                 {'name': 'Matching Number'}, {'name': 'Initial Balance', 'class': 'number'},
                 {'name': 'Debit', 'class': 'number'}, {'name': 'Credit', 'class': 'number'},
                 {'name': 'Balance', 'class': 'number'}]]}
        x = self.with_context({'model': 'account.partner.ledger'}).print_pdf(options)
        return x

    def bs_partner_ledger_get_xlsx(self, options, response=None):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        _logger.error("1 report ")
        sheet = workbook.add_worksheet(self._get_report_name()[:31])
        date_default_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'font_size': 12})
        level_0_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
        level_1_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_2_col1_total_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_2_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_3_col1_total_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        # Set the first column width to 50
        sheet.set_column(0, 0, 20)
        sheet.set_row(0, 50)
        sheet.set_column(1, 1, 30)
        sheet.set_column(3, 3, 40)
        sheet.set_column(4, 4, 70)
        sheet.set_column(5, 5, 20)
        sheet.set_column(6, 6, 20)
        sheet.set_column(7, 7, 20)
        sheet.set_column(8, 8, 20)
        sheet.set_column(9, 9, 20)
        sheet.set_column(10, 10, 20)
        sheet.set_column(11, 11, 20)
        sheet.set_column(12, 12, 20)
        sheet.set_column(13, 13, 20)
        sheet.set_column(14, 14, 20)
        sheet.set_column(15, 15, 20)
        sheet.set_column(16, 16, 20)
        sheet.set_column(17, 17, 20)
        sheet.set_column(18, 18, 20)
        sheet.set_column(19, 19, 20)

        y_offset = 0
        headers, lines = self.with_context(no_format=True, print_mode=True, prefetch_fields=False)._get_table(options)
        x_offset = 0
        # company details
        _logger.error("2 report ")
        comp_offset = 3
        partner = self.env['res.partner'].sudo().browse(options.get('partner_ids')[0])
        #         sheet.write(y_offset, x_offset, 'logo.png')
        #         image_data = io.BytesIO(partner.company_id.logo.read())
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        _logger.error("% report ", base_url)
        url = base_url + '/buildmart/static/src/images/logo.png'
        _logger.error("3 report ")
        image_data = io.BytesIO(urlopen(url).read())
        _logger.error("4 report ")
        sheet.insert_image(y_offset, x_offset, url, {'image_data': image_data})
        sheet.write(y_offset, comp_offset, partner.company_id.name, title_style)
        y_offset += 1
        sheet.write(y_offset, comp_offset, partner.company_id.street)
        y_offset += 1
        sheet.write(y_offset, comp_offset, partner.company_id.street2)
        sheet.write(y_offset, x_offset, 'Partner Ledger')
        comaddr = ','.join([partner.company_id.city, partner.company_id.state_id.name])
        y_offset += 1
        sheet.write(y_offset, comp_offset, comaddr)
        sheet.write(y_offset, x_offset, 'Customer Code:')
        comp_contry_pin = ','.join([partner.company_id.country_id.name, partner.company_id.zip])
        y_offset += 1
        sheet.write(y_offset, comp_offset, comp_contry_pin)
        y_offset += 1
        sheet.write(y_offset, x_offset, 'Customer Name:')
        sheet.write(y_offset, x_offset + 1, partner.name)
        sheet.write(y_offset, comp_offset, 'CIN:')
        sheet.write(y_offset, comp_offset + 1, partner.company_id.company_registry)
        y_offset += 1
        sheet.write(y_offset, x_offset, 'GSTIN:')
        sheet.write(y_offset, x_offset + 1, partner.name)
        sheet.write(y_offset, comp_offset, 'GSTIN:')
        sheet.write(y_offset, comp_offset + 1, partner.company_id.vat)
        y_offset += 1
        sheet.write(y_offset, x_offset, 'Address:')
        sheet.write(y_offset, x_offset + 1, partner.street)
        sheet.write(y_offset, comp_offset, 'PAN:')
        sheet.write(y_offset, comp_offset + 1, '')
        y_offset += 1
        sheet.write(y_offset, x_offset + 1, partner.street2)
        sheet.write(y_offset, comp_offset, 'Sales Person:')
        sheet.write(y_offset, comp_offset + 1, '')
        y_offset += 1
        addr = ''
        if partner.city and partner.district_id and partner.state_id:
            addr = ','.join([partner.city, partner.district_id.name, partner.state_id.name])
        sheet.write(y_offset, x_offset + 1, addr)
        sheet.write(y_offset, comp_offset, 'Sales Category:')
        sheet.write(y_offset, comp_offset + 1, '')
        y_offset += 1
        contry_pin = ''
        if partner.country_id and partner.zip:
            contry_pin = ','.join([partner.country_id.name, partner.zip])
        sheet.write(y_offset, x_offset + 1, contry_pin)
        sheet.write(y_offset, comp_offset, 'Email:')
        sheet.write(y_offset, comp_offset + 1, partner.company_id.email)
        y_offset += 1
        sheet.write(y_offset, comp_offset, 'Customer Care:')
        sheet.write(y_offset, comp_offset + 1, partner.company_id.phone)
        y_offset += 3
        # Add headers.
        headers = options.get('headers')
        for header in headers:
            for column in header:
                column_name_formated = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                colspan = column.get('colspan', 1)
                if colspan == 1:
                    sheet.write(y_offset, x_offset, column_name_formated, title_style)
                else:
                    sheet.merge_range(y_offset, x_offset, y_offset, x_offset + colspan - 1, column_name_formated,
                                      title_style)
                x_offset += colspan
            y_offset += 1

        # Add lines.
        for y in range(0, len(lines)):
            if y:
                level = lines[y].get('level')
                if lines[y].get('caret_options'):
                    style = level_3_style
                    col1_style = level_3_col1_style
                elif level == 0:
                    y_offset += 1
                    style = level_0_style
                    col1_style = style
                elif level == 1:
                    style = level_1_style
                    col1_style = style
                elif level == 2:
                    style = level_2_style
                    col1_style = 'total' in lines[y].get('class', '').split(
                        ' ') and level_2_col1_total_style or level_2_col1_style
                elif level == 3:
                    style = level_3_style
                    col1_style = 'total' in lines[y].get('class', '').split(
                        ' ') and level_3_col1_total_style or level_3_col1_style
                else:
                    style = default_style
                    col1_style = default_col1_style

                # write the first column, with a specific style to manage the indentation
                cell_type, cell_value = self._get_cell_type_value(lines[y])
                if cell_value == 'Total':
                    lines[y]['colspan'] = 16
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
                else:
                    sheet.write(y + y_offset, 0, cell_value, col1_style)

                # write all the remaining cells
                for x in range(1, len(lines[y]['columns']) + 1):
                    cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
                    if cell_type == 'date':
                        sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value,
                                             date_default_style)
                    else:
                        sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        return generated_file


class ReportPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger"
    
    @api.model
    def _get_report_line_total(self, options, initial_balance, debit, credit, balance):
        columns = [
            {'name': self.format_value(initial_balance), 'class': 'number'},
            {'name': self.format_value(debit), 'class': 'number'},
            {'name': self.format_value(credit), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': ''})
        columns.append({'name': self.format_value(balance), 'class': 'number'})
        return {
            'id': 'partner_ledger_total_%s' % self.env.company.id,
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': columns,
            'colspan': 8 if options.get('sitename',False) else 7,
        }

    def _get_columns_name(self, options):
        to_display_sitename = options.get('sitename',False) #TODO:open on condition
        columns = [
            {'name': _('Date'), 'class': 'date'},
            {'name': _('JRNL')},
            {'name': _('Account')}]
        if to_display_sitename:
            columns += [{'name': _('Site Name'), 'class': 'sitename'}]
        columns += [
            {'name': _('Ref')},
            {'name': _('Due Date'), 'class': 'date'},
            {'name': _('Matching Number')},
            {'name': _('Delay days')},
            # {'name': _('Quantity')},
            {'name': _('Initial Balance'), 'class': 'number'},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'}]

        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': _('Amount Currency'), 'class': 'number'})
        columns.append({'name': _('Balance'), 'class': 'number'})
        return columns

    # Overridden
    @api.model
    def _get_query_amls(self, options, expanded_partner=None, offset=None, limit=None):
        ''' Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:             The report options.
        :param expanded_partner:    The res.partner record corresponding to the expanded line.
        :param offset:              The offset of the query (used by the load more).
        :param limit:               The limit of the query (used by the load more).
        :return:                    (query, params)
        '''
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        # Get sums for the account move lines.
        # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
        if expanded_partner:
            domain = [('partner_id', '=', expanded_partner.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('partner_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        new_options = self._get_options_sum_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        query = '''
            SELECT
                account_move_line.id,
                account_move_line.date,
                account_move_line.date_maturity,
                account_move_line.name,
                account_move_line.ref,
                account_move_line.company_id,
                account_move_line.account_id,
                account_move_line.payment_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.matching_number,
                ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                account_move_line__move_id.name         AS move_name,
                company.currency_id                     AS company_currency_id,
                partner.name                            AS partner_name,
                account_move_line__move_id.move_type         AS move_type,
                account.code                            AS account_code,
                account.name                            AS account_name,
                journal.code                            AS journal_code,
                journal.name                            AS journal_name,
                account_move_line__move_id.sitename_id AS sitename,
                account_move_line__move_id.invoice_date_due AS delay_days,
                account_move_line__move_id.payment_state AS payment_state,
                account_move_line__move_id.paid_days_count AS paid_days_count
            FROM account_move_line
            LEFT JOIN account_move account_move_line__move_id ON account_move_line__move_id.id = account_move_line.move_id
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            LEFT JOIN res_company company               ON company.id = account_move_line.company_id
            LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
            LEFT JOIN account_account account           ON account.id = account_move_line.account_id
            LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
            WHERE %s 
            ORDER BY account_move_line.date,account_move_line.id
        ''' % (ct_query, where_clause)

        if offset:
            query += ' OFFSET %s '
            where_params.append(offset)
        if limit:
            query += ' LIMIT %s '
            where_params.append(limit)

        return query, where_params
    
    def get_quantity(self, partner):
        quantity = ''
        if partner:
            moves = self.env['account.move'].search([('partner_id','=',partner.id),('state','=','posted')])
            if moves:
                for read in self.env['account.move.line'].read_group(
                        domain=[('move_id','in',moves.ids),('exclude_from_invoice_tab','=',False),
                                ('product_id.detailed_type','!=','service')],
                        fields=['quantity', 'product_uom_id'],
                        groupby=['product_uom_id'],):
                    if read['product_uom_id']:
                        if not quantity:
                            quantity += str(abs(read['quantity'])) + ' ' + \
                                        self.env['uom.uom'].browse(int(read['product_uom_id'][0])).name + ' '
                        else:
                            if not '+More' in quantity: quantity += ' +More'
        return quantity

    # Each partner
    def aml_qty(self, aml_id, payment):
        quantity = ''
        if payment:
            return quantity
        if aml_id:
            move_line = self.env['account.move.line'].browse(int(aml_id))
            if move_line:
                move = self.env['account.move'].browse(int(move_line.move_id))
                lines = move.invoice_line_ids
                for read in self.env['account.move.line'].read_group(
                        domain=[('id','in',lines.ids),('exclude_from_invoice_tab','=',False),('product_id.detailed_type','!=','service')],
                        fields=['quantity', 'product_uom_id'],
                        groupby=['product_uom_id'],):
                    if read['product_uom_id']:
                        if not quantity:
                            quantity += str(read['quantity']) + ' ' + \
                                        self.env['uom.uom'].browse(int(read['product_uom_id'][0])).name + ' '
                        else:
                            if not '+More' in quantity: quantity += ' +More'
        return quantity

    # extended
    @api.model
    def _get_report_line_partner(self, options, partner, initial_balance, debit, credit, balance):
        to_display_sitename = options.get('sitename', False)
        columns = []
        company_currency = self.env.company.currency_id
        unfold_all = self._context.get('print_mode') and not options.get('unfolded_lines')
        if to_display_sitename:
            columns += [{'name': '', 'class': 'sitename'}]
        columns += [{'name': ''}]
        columns += [
            {'name': self.format_value(initial_balance), 'class': 'number'},
            {'name': self.format_value(debit), 'class': 'number'},
            {'name': self.format_value(credit), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': ''})
        columns.append({'name': self.format_value(balance), 'class': 'number'})

        return {
            'id': 'partner_%s' % (partner.id if partner else 0),
            'partner_id': partner.id if partner else None,
            'name': partner is not None and (partner.name or '')[:128] or _('Unknown Partner'),
            'columns': columns,
            'level': 2,
            'trust': partner.trust if partner else None,
            'unfoldable': not company_currency.is_zero(debit) or not company_currency.is_zero(credit),
            'unfolded': 'partner_%s' % (partner.id if partner else 0) in options['unfolded_lines'] or unfold_all,
            'colspan': 6,
        }

    # overridden
    @api.model
    def _get_report_line_move_line(self, options, partner, aml, cumulated_init_balance, cumulated_balance):
        to_display_sitename = options.get('sitename', False)
        ledger_type = options.get('ledger_type', False)
        if ledger_type == 'bs':
            if aml['payment_id']:
                caret_type = 'account.payment'
            else:
                caret_type = 'account.move'
            item_desc = ''
            total_qty = ''
            cus_ref = ''
            site_name = ''
            del_loc = ''
            vehicl_numb = ''
            pay_trm = ''
            amt_due = 0.0
            date_payment = ''
            delay_days = ''
            if to_display_sitename: sitename = ''

            if caret_type == 'account.move':
                account_move = self.env['account.move'].sudo().browse(int(aml['id']))
                if to_display_sitename and account_move.sitename_id:
                    sitename = account_move.sitename_id.name
                if account_move.partner_shipping_id:
                    del_loc = ','.join(
                        [account_move.partner_shipping_id.street, account_move.partner_shipping_id.street2,
                         account_move.partner_shipping_id.city])
                amt_due = account_move.amount_residual
                total_qty = sum(account_move.invoice_line_ids.mapped('quantity'))
                item_desc = account_move.invoice_line_ids.mapped('product_id').mapped('product_tmpl_id').name
                so = self.env['sale.order'].sudo().search([('name', '=', account_move.invoice_origin)])
                if so: pay_trm = so.payment_term_id.name
                delay_days = account_move.invoice_date_due
                date_payment = account_move.invoice_payments_widget
            date_maturity = aml['date_maturity'] and \
                            format_date(self.env, fields.Date.from_string(aml['date_maturity']))
            columns = [
                {'name': aml['journal_code']},
                {'name': aml['account_code']}]

            if to_display_sitename:
                columns += [{'name': sitename}]

            columns += [
                {'name': self._format_aml_name(aml['name'], aml['ref'], aml['move_name'])},
                {'name': item_desc},
                {'name': total_qty},
                {'name': cus_ref},
                {'name': site_name},
                {'name': del_loc},
                {'name': vehicl_numb},
                {'name': aml['matching_number'] or ''},
                {'name': pay_trm},
                {'name': amt_due, 'class': 'number'},
                {'name': date_maturity or '', 'class': 'date'},
                {'name': date_payment, 'class': 'date'},
                {'name': delay_days},
                {'name': self.format_value(cumulated_init_balance), 'class': 'number'},
                {'name': self.format_value(aml['debit'], blank_if_zero=True), 'class': 'number'},
                {'name': self.format_value(aml['credit'], blank_if_zero=True), 'class': 'number'},
            ]
            if self.user_has_groups('base.group_multi_currency'):
                if aml['currency_id']:
                    currency = self.env['res.currency'].browse(aml['currency_id'])
                    formatted_amount = self.format_value(aml['amount_currency'], currency=currency, blank_if_zero=True)
                    columns.append({'name': formatted_amount, 'class': 'number'})
                else:
                    columns.append({'name': ''})
            columns.append({'name': self.format_value(cumulated_balance), 'class': 'number'})
            return {
                'id': aml['id'],
                'parent_id': 'partner_%s' % partner.id,
                'name': format_date(self.env, aml['date']),
                'class': 'text',  # do not format as date to prevent text centering
                'columns': columns,
                'caret_options': caret_type,
                'level': 2,
            }

        if aml['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move'

        date_maturity = aml['date_maturity'] and aml['date_maturity'].strftime('%d-%B-%Y')

        if to_display_sitename:
            sitename = ""
            if aml['sitename']:
                sitename = self.env['bs.sitename'].browse(int(aml['sitename'])).name
            else:
                mv_line = self.env['account.move.line'].browse(int(aml['id']))
                if mv_line:
                    if mv_line.sitename_id:
                        sitename = mv_line.sitename_id.name
                if aml['payment_id']:
                    payment = self.env['account.payment'].browse(int(aml['payment_id']))
                    if payment:
                        if payment.sitename_id:
                            sitename = payment.sitename_id.name
                    
        delay_days = ''
        if caret_type == 'account.move':
            if aml['payment_state'] == 'not_paid':
                date_format = "%Y-%m-%d"
                invoice_days = datetime.strptime(str(aml['delay_days']), date_format)
                today = datetime.today()
                diff = today.date() - invoice_days.date()
                delay_days = diff.days
            else:
                delay_days =  aml['paid_days_count']
        
        
        columns = [
            {'name': aml['journal_code']},
            {'name': aml['account_code']}]
        if to_display_sitename:
            columns += [{'name': sitename, 'class': 'sitename'}]
        columns += [
            {'name': self._format_aml_name(aml['name'], aml['ref'], aml['move_name'])},
            {'name': date_maturity or '', 'class': 'date'},
            {'name': aml['matching_number'] or ''},
            {'name': delay_days},
            # {'name': self.aml_qty(aml['id'],aml['payment_id']) or ''},
            {'name': self.format_value(cumulated_init_balance), 'class': 'number'},
            {'name': self.format_value(aml['debit'], blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(aml['credit'], blank_if_zero=True), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            if aml['currency_id']:
                currency = self.env['res.currency'].browse(aml['currency_id'])
                formatted_amount = self.format_value(aml['amount_currency'], currency=currency, blank_if_zero=True)
                columns.append({'name': formatted_amount, 'class': 'number'})
            else:
                columns.append({'name': ''})
        columns.append({'name': self.format_value(cumulated_balance), 'class': 'number'})
        return {
            'id': aml['id'],
            'parent_id': 'partner_%s' % partner.id if partner else False,
            'name': aml['date'].strftime('%d-%B-%Y') if aml['date'] else '',
            'class': 'text',  # do not format as date to prevent text centering
            'columns': columns,
            'caret_options': caret_type,
            'level': 2,
        }
        
    # def _get_report_name(self):
    #     report_name = 'Partner Ledger Admin'
    #     partner = self._context.get('partner_ids',[])
    #     if partner:
    #         if len(partner) == 1:
    #             report_name += partner.name
    #     return _(report_name)
