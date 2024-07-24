from odoo import api, fields, models, tools
from itertools import groupby

class L10nInReportAccount(models.AbstractModel):
    _inherit = "l10n.in.report.account"
    
    def group_report_lines(self, group_fields, fields_values, fields):
        res = []
        fields_values = sorted(fields_values, key=lambda s: [s.get(g, '') for g in group_fields])
        for _, grouped_values in groupby(fields_values, lambda x: [x.get(g, '') for g in group_fields]):
            vals = {}
            first_grouped_value = {}
            for grouped_value in grouped_values:
                for field in fields:
                    vals.setdefault(str(field), 0)
                    vals[field] += grouped_value.get(field, 0)
                first_grouped_value.update(grouped_value)
            for group_field in group_fields:
                vals.setdefault(group_field, first_grouped_value.get(group_field, ''))
                
            for key in vals:
                if isinstance(vals[key], float):
                    vals[key] = round(vals[key], 3)
            res.append(vals)
        return res


class L10nInProductHsnReport(models.Model):
    _inherit = "l10n_in.product.hsn.report"
    
    def _select(self):
        select_str = """SELECT aml.id AS id,
            aml.move_id AS account_move_id,
            aml.partner_id AS partner_id,
            aml.product_id,
            aml.product_uom_id AS uom_id,
            am.date,
            am.journal_id,
            aj.company_id,
            CASE WHEN pt.l10n_in_hsn_code IS NULL THEN '' ELSE pt.l10n_in_hsn_code END AS hsn_code,
            CASE WHEN pt.l10n_in_hsn_description IS NULL THEN '' ELSE pt.l10n_in_hsn_description END AS hsn_description,
            CASE WHEN uom.l10n_in_code IS NULL THEN '' ELSE uom.l10n_in_code END AS l10n_in_uom_code,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_sgst', 'tax_report_line_sgst_rc')) OR at.l10n_in_reverse_charge = True
                THEN 0
                ELSE (select quantity from account_move_line where move_id = aml.move_id order by id desc limit 1)
                END * (CASE WHEN am.move_type in ('in_refund','out_refund') THEN -1 ELSE 1 END)
                AS quantity,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_igst', 'tax_report_line_igst_rc'))
                THEN aml.balance * (CASE WHEN aj.type = 'sale' and am.move_type != 'out_refund' THEN -1 ELSE 1 END)
                ELSE 0
                END * (CASE WHEN am.move_type in ('in_refund','out_refund') THEN -1 ELSE 1 END)
                AS igst_amount,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_cgst', 'tax_report_line_cgst_rc'))
                THEN aml.balance * (CASE WHEN aj.type = 'sale' and am.move_type != 'out_refund' THEN -1 ELSE 1 END)
                ELSE 0
                END * (CASE WHEN am.move_type in ('in_refund','out_refund') THEN -1 ELSE 1 END)
                AS cgst_amount,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_sgst', 'tax_report_line_sgst_rc'))
                THEN aml.balance * (CASE WHEN aj.type = 'sale' and am.move_type != 'out_refund' THEN -1 ELSE 1 END)
                ELSE 0
                END * (CASE WHEN am.move_type in ('in_refund','out_refund') THEN -1 ELSE 1 END)
                AS  sgst_amount,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_cess', 'tax_report_line_cess_rc'))
                THEN aml.balance * (CASE WHEN aj.type = 'sale' and am.move_type != 'out_refund' THEN -1 ELSE 1 END)
                ELSE 0
                END * (CASE WHEN am.move_type in ('in_refund','out_refund') THEN -1 ELSE 1 END)
                AS cess_amount,
            CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_sgst', 'tax_report_line_sgst_rc'))
                THEN 0
                ELSE (CASE WHEN aml.tax_line_id IS NOT NULL THEN aml.tax_base_amount ELSE aml.balance * (CASE WHEN aj.type = 'sale' THEN -1 ELSE 1 END) END)
                END * (CASE WHEN am.move_type in ('in_refund','out_refund') THEN -1 ELSE 1 END)
                AS price_total,
            ((CASE WHEN tag_rep_ln.account_tax_report_line_id IN
                (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('tax_report_line_sgst', 'tax_report_line_sgst_rc'))
                THEN 0
                ELSE (CASE WHEN aml.tax_line_id IS NOT NULL THEN aml.tax_base_amount ELSE 1 END)
                    END) + (aml.balance * (CASE WHEN aj.type = 'sale' and am.move_type != 'out_refund' THEN -1 ELSE 1 END))
                 )* (CASE WHEN am.move_type in ('in_refund','out_refund') THEN -1 ELSE 1 END)
                AS total
        """
        return select_str