# -*- coding: utf-8 -*-
import base64
import io
from datetime import timedelta
from urllib.parse import quote

from odoo import _, fields, models
from odoo.tools import html2plaintext


class SellingRateAnalysisWizard(models.TransientModel):
    _name = 'selling.rate.analysis.wizard'
    _description = 'Selling Rate Analysis Report by Customers and BU'

    def _get_sale_person_domain(self):
        current_user = self.env.user
        if current_user.has_group('sales_team.group_sale_manager'):
            partners = self.env['res.partner'].search([])
            users = partners.mapped('sale_pic_ids')
            return [('id', 'in', users.ids)]
        return [('id', '=', current_user.id)]

    from_date = fields.Date(string='From Date', required=True)
    to_date = fields.Date(string='To Date', required=True)
    bu_ids = fields.Many2many(
        'account.analytic.account',
        'selling_rate_wizard_bu_rel',
        'wizard_id',
        'analytic_account_id',
        string='BU',
        domain="[('plan_id.is_bu', '=', True)]",
    )
    sub_bu_ids = fields.Many2many(
        'account.analytic.account',
        'selling_rate_wizard_sub_bu_rel',
        'wizard_id',
        'analytic_account_id',
        string='Sub-BU',
        domain="[('plan_id.is_sub_bu', '=', True)]",
    )
    sale_pic_ids = fields.Many2many(
        'res.users',
        'selling_rate_wizard_sale_pic_rel',
        'wizard_id',
        'user_id',
        string='Sale PIC',
        domain=lambda self: self._get_sale_person_domain(),
    )
    # Kept for old cached views until module upgrade; wizard uses currency_ids.
    currency_id = fields.Many2one('res.currency', string='Currency')
    currency_ids = fields.Many2many(
        'res.currency',
        'selling_rate_wizard_currency_rel',
        'wizard_id',
        'currency_id',
        string='Currency',
    )
    excel_file = fields.Binary(string='Excel File')
    file_name = fields.Char(string='File Name')

    def _format_report_date(self, date_value):
        """Format date like: 1 July 2026"""
        if not date_value:
            return ''
        return f"{date_value.day} {date_value.strftime('%B %Y')}"

    def _join_names(self, records, name_field='name'):
        return ','.join(records.mapped(name_field))

    def _get_analytic_account_ids_from_distribution(self, analytic_distribution):
        if not analytic_distribution:
            return set()
        return {
            int(account_id)
            for account_id in ','.join(analytic_distribution.keys()).split(',')
            if account_id
        }

    def _line_matches_bu_filters(self, line, analytic_filter_ids):
        line_analytic_ids = self._get_analytic_account_ids_from_distribution(line.analytic_distribution)
        return bool(line_analytic_ids & analytic_filter_ids)

    def _get_analytic_filter_ids(self):
        """BU/Sub-BU selected in wizard, or all analytics under is_bu / is_sub_bu plans."""
        self.ensure_one()
        analytic_filter_ids = set(self.bu_ids.ids) | set(self.sub_bu_ids.ids)
        if analytic_filter_ids:
            return analytic_filter_ids
        return set(self.env['account.analytic.account'].search([
            '|',
            ('plan_id.is_bu', '=', True),
            ('plan_id.is_sub_bu', '=', True),
        ]).ids)

    def _get_order_status(self, order, report_date):
        effective_date = fields.Date.to_date(order.date_order) if order.date_order else False
        validity_date = order.validity_date
        if effective_date and validity_date and effective_date <= report_date <= validity_date:
            return 'Active'
        return 'Inactive'

    def _get_gp_percent(self, line):
        if not line.cost:
            return 0.0
        return (line.gross_profit / line.cost) * 100.0

    def _get_report_rows(self, report_date):
        """
        Find confirmed sale orders from wizard filters, then map matching
        order lines into Excel rows.
        """
        self.ensure_one()
        date_from_dt = fields.Datetime.to_datetime(self.from_date)
        date_to_dt = fields.Datetime.to_datetime(self.to_date) + timedelta(days=1)

        domain = [
            ('state', '=', 'sale'),
            ('revise_state', '=', False),
            ('create_date', '>=', date_from_dt),
            ('create_date', '<', date_to_dt),
        ]
        if self.currency_ids:
            domain.append(('currency_id', 'in', self.currency_ids.ids))
        elif self.currency_id:
            domain.append(('currency_id', '=', self.currency_id.id))
        if 'is_job_order' in self.env['sale.order']._fields:
            domain.append(('is_job_order', '=', False))
        if self.sale_pic_ids:
            domain.append(('user_id', 'in', self.sale_pic_ids.ids))

        orders = self.env['sale.order'].search(domain, order='create_date, id')
        analytic_filter_ids = self._get_analytic_filter_ids()

        rows = []
        for order in orders:
            status = self._get_order_status(order, report_date)
            lines = order.order_line.filtered(lambda l: not l.display_type)
            for line in lines:
                if not self._line_matches_bu_filters(line, analytic_filter_ids):
                    continue
                rows.append({
                    'customer_name': order.partner_id.name or '',
                    'quotation_number': order.name or '',
                    'effective_date': self._format_report_date(fields.Date.to_date(order.date_order)) if order.date_order else '',
                    'validity_date': self._format_report_date(order.validity_date) if order.validity_date else '',
                    'payment_terms': order.payment_term_id.name or '',
                    'status': status,
                    'sale_pic': order.user_id.name or '',
                    'product': line.product_template_id.name or '',
                    'descriptions': line.name or '',
                    'uom': line.product_uom.name or '',
                    'selling_rate': line.price_unit or 0.0,
                    'cost_rate': line.cost or 0.0,
                    'gross_profit': line.gross_profit or 0.0,
                    'gp_percent': self._get_gp_percent(line),
                    'currency': line.inv_currency_id.name or '',
                    'remark': html2plaintext(line.remark or '').strip(),
                })
        return rows

    def action_print(self):
        self.ensure_one()
        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        today = fields.Date.context_today(self)
        today_label = self._format_report_date(today)
        from_label = self._format_report_date(self.from_date)
        to_label = self._format_report_date(self.to_date)
        report_rows = self._get_report_rows(today)

        sale_pic_names = self._join_names(self.sale_pic_ids, 'name')
        bu_names = self._join_names(self.bu_ids, 'name')
        sub_bu_names = self._join_names(self.sub_bu_ids, 'name')

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Selling Rate Analysis')

        title_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'left', 'valign': 'vcenter'})
        header_format = workbook.add_format({'bold': True, 'border': 1})
        text_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        percent_format = workbook.add_format({'border': 1, 'num_format': '0.00%'})

        header_lines = [
            self.env.company.name or '',
            'Selling Rate Analysis Report by Customers and BU',
            f'Duration : {from_label} / {to_label} (Report Export Date : {today_label})',
            f'SalePIC  : {sale_pic_names}',
            f'BU  : {bu_names}',
            f'Sub Bu : {sub_bu_names}',
        ]
        rowx = 0
        for line in header_lines:
            # Merge first 5 columns (A-E)
            sheet.merge_range(rowx, 0, rowx, 4, line, title_format)
            rowx += 1
        rowx += 1

        headers = [
            'No',
            'Customer Name',
            'Quotation Number',
            'Effective Date',
            'Validity Date',
            'Payment Terms',
            'Status',
            'SalePIC',
            'Product',
            'Descriptions',
            'UOM',
            'Selling Rate',
            'Cost Rate',
            'Gross Profit',
            'GP(%)',
            'Currency',
            'Remark',
        ]
        for colx, header in enumerate(headers):
            sheet.write(rowx, colx, header, header_format)
            sheet.set_column(colx, colx, max(12, len(header) + 2))
        rowx += 1

        for index, row in enumerate(report_rows, start=1):
            sheet.write(rowx, 0, index, text_format)
            sheet.write(rowx, 1, row['customer_name'], text_format)
            sheet.write(rowx, 2, row['quotation_number'], text_format)
            sheet.write(rowx, 3, row['effective_date'], text_format)
            sheet.write(rowx, 4, row['validity_date'], text_format)
            sheet.write(rowx, 5, row['payment_terms'], text_format)
            sheet.write(rowx, 6, row['status'], text_format)
            sheet.write(rowx, 7, row['sale_pic'], text_format)
            sheet.write(rowx, 8, row['product'], text_format)
            sheet.write(rowx, 9, row['descriptions'], text_format)
            sheet.write(rowx, 10, row['uom'], text_format)
            sheet.write(rowx, 11, row['selling_rate'], number_format)
            sheet.write(rowx, 12, row['cost_rate'], number_format)
            sheet.write(rowx, 13, row['gross_profit'], number_format)
            # Excel % format expects 0.125 for 12.5%
            sheet.write(rowx, 14, (row['gp_percent'] or 0.0) / 100.0, percent_format)
            sheet.write(rowx, 15, row['currency'], text_format)
            sheet.write(rowx, 16, row['remark'], text_format)
            rowx += 1

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = f'Selling Rate Analysis Report by Customers and BU ({today_label}).xlsx'
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{quote(fname)}?download=true',
            'target': 'new',
        }
