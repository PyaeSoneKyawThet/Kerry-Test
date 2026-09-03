from odoo import models, fields, _
from datetime import date
from collections import defaultdict
import io
import base64
import json


class KMTLYearlyRevenueComparisonWizard(models.TransientModel):
    _name = 'kmtl.yearly.revenue.comparison'
    _description = 'Yearly Revenue Comparison Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    partner_ids = fields.Many2many('res.partner', string='Customers')
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _format_duration_date(self, value, with_day=True):
        if not value:
            return ''
        if with_day:
            return f"{value.day} {value.strftime('%b %Y')}"
        return value.strftime('%b %Y')

    def _years_between(self, start_date, end_date):
        return list(range(start_date.year, end_date.year + 1))

    def _get_sub_bu_account_ids(self):
        AnalyticAccount = self.env['account.analytic.account']
        Plan = self.env['account.analytic.plan']
        if 'is_sub_bu' in Plan._fields:
            return set(AnalyticAccount.search([('plan_id.is_sub_bu', '=', True)]).ids)
        return set(AnalyticAccount.search([('plan_id.name', 'ilike', 'sub bu')]).ids)

    def _get_analytic_ids_from_distribution(self, analytic_distribution):
        if not analytic_distribution:
            return set()
        if isinstance(analytic_distribution, str):
            analytic_distribution = json.loads(analytic_distribution)
        return {
            int(account_id)
            for account_id in ','.join(analytic_distribution.keys()).split(',')
            if account_id
        }

    def _get_sub_bu_name(self, analytic_distribution, sub_bu_ids, analytic_names):
        line_ids = self._get_analytic_ids_from_distribution(analytic_distribution)
        matched = sorted(line_ids & sub_bu_ids)
        if not matched:
            return ''
        return analytic_names.get(matched[0], '')

    def _gather_data(self):
        self.ensure_one()
        start = self.date_from
        stop = self.date_to
        years = self._years_between(start, stop)
        company_id = self.env.company.id
        sub_bu_ids = self._get_sub_bu_account_ids()

        partner_filter_sql = ''
        params = [start, stop, company_id]
        if self.partner_ids:
            partner_filter_sql = 'AND COALESCE(aml.partner_id, am.partner_id) IN %s'
            params.append(tuple(self.partner_ids.ids))

        query = (
            "SELECT COALESCE(aml.partner_id, am.partner_id), aml.date, "
            "aml.credit, aml.debit, aml.analytic_distribution "
            "FROM account_move_line aml "
            "JOIN account_move am ON aml.move_id = am.id "
            "JOIN account_account a ON aml.account_id = a.id "
            "WHERE aml.date >= %s AND aml.date <= %s "
            "AND a.account_type = 'income' "
            "AND am.state = 'posted' "
            "AND aml.company_id = %s "
            + partner_filter_sql
        )
        self.env.cr.execute(query, tuple(params))
        rows = self.env.cr.fetchall()

        all_analytic_ids = set()
        for _partner_id, _aml_date, _credit, _debit, distribution in rows:
            all_analytic_ids |= self._get_analytic_ids_from_distribution(distribution)
        analytic_names = {
            rec.id: rec.name
            for rec in self.env['account.analytic.account'].browse(list(all_analytic_ids))
        }

        # amounts[(partner_id, sub_bu_name)][year] = amount
        amounts = defaultdict(lambda: defaultdict(float))
        partner_ids_found = set()

        for partner_id, aml_date, credit, debit, distribution in rows:
            if isinstance(aml_date, date):
                year = aml_date.year
            else:
                year = fields.Date.to_date(aml_date).year
            if year not in years:
                continue
            sub_bu_name = self._get_sub_bu_name(distribution, sub_bu_ids, analytic_names)
            amount = float(credit or 0.0) - float(debit or 0.0)
            amounts[(partner_id or 0, sub_bu_name)][year] += amount
            partner_ids_found.add(partner_id or 0)

        if self.partner_ids:
            partners = self.partner_ids.sorted(key=lambda p: p.name or '')
        else:
            found_ids = [pid for pid in partner_ids_found if pid]
            partners = self.env['res.partner'].browse(found_ids).sorted(
                key=lambda p: p.name or ''
            )

        # Build grouped structure for Excel
        grouped = []
        for partner in partners:
            sub_bu_rows = []
            partner_keys = [
                (pid, sub_bu)
                for (pid, sub_bu) in amounts.keys()
                if pid == partner.id
            ]
            partner_keys.sort(key=lambda item: item[1] or '')
            for _pid, sub_bu in partner_keys:
                year_amounts = [amounts[(_pid, sub_bu)].get(year, 0.0) for year in years]
                if any(year_amounts):
                    sub_bu_rows.append({
                        'sub_bu': sub_bu or '-',
                        'amounts': year_amounts,
                    })
            if not sub_bu_rows and self.partner_ids:
                # Selected customer with no income lines still shown empty
                sub_bu_rows.append({
                    'sub_bu': '-',
                    'amounts': [0.0] * len(years),
                })
            if sub_bu_rows:
                customer_total = [
                    sum(row['amounts'][idx] for row in sub_bu_rows)
                    for idx in range(len(years))
                ]
                grouped.append({
                    'partner_name': partner.name or '',
                    'rows': sub_bu_rows,
                    'total': customer_total,
                })

        # Lines with no customer → None group (same as Quarterly report)
        if not self.partner_ids and 0 in partner_ids_found:
            none_keys = [(pid, sub_bu) for (pid, sub_bu) in amounts.keys() if not pid]
            none_keys.sort(key=lambda item: item[1] or '')
            sub_bu_rows = []
            for _pid, sub_bu in none_keys:
                year_amounts = [amounts[(_pid, sub_bu)].get(year, 0.0) for year in years]
                if any(year_amounts):
                    sub_bu_rows.append({
                        'sub_bu': sub_bu or '-',
                        'amounts': year_amounts,
                    })
            if sub_bu_rows:
                customer_total = [
                    sum(row['amounts'][idx] for row in sub_bu_rows)
                    for idx in range(len(years))
                ]
                grouped.append({
                    'partner_name': _('None'),
                    'rows': sub_bu_rows,
                    'total': customer_total,
                })

        grand_total = [
            sum(group['total'][idx] for group in grouped)
            for idx in range(len(years))
        ]
        return years, grouped, grand_total

    def action_export_xlsx(self):
        self.ensure_one()
        years, grouped, grand_total = self._gather_data()

        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Yearly Revenue Comparison')

        title_format = workbook.add_format({'bold': True, 'font_size': 12})
        header_format = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
        })
        text_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        number_format = workbook.add_format({
            'border': 1, 'num_format': '#,##0', 'valign': 'vcenter',
        })
        total_text_format = workbook.add_format({
            'bold': True, 'border': 1, 'valign': 'vcenter',
        })
        total_number_format = workbook.add_format({
            'bold': True, 'border': 1, 'num_format': '#,##0', 'valign': 'vcenter',
        })
        empty_dash_format = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
        })

        # Header
        rowx = 0
        sheet.write(rowx, 0, self.env.company.name or '', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Yearly Revenue Comparison', title_format)
        rowx += 1
        duration = (
            f"Duration : From {self._format_duration_date(self.date_from, with_day=True)} "
            f"To {self._format_duration_date(self.date_to, with_day=False)}"
        )
        sheet.write(rowx, 0, duration, title_format)
        rowx += 1
        currency_name = self.env.company.currency_id.name or 'MMK'
        sheet.write(rowx, 0, f'Currency : {currency_name}', title_format)
        rowx += 2

        # Table header - two rows (Year group + FY columns)
        last_col = 1 + len(years)
        sheet.write(rowx, 0, 'Customer Name', header_format)
        sheet.write(rowx, 1, 'Sub-BU', header_format)
        if years:
            if len(years) == 1:
                sheet.write(rowx, 2, 'Year', header_format)
            else:
                sheet.merge_range(rowx, 2, rowx, last_col, 'Year', header_format)
        rowx += 1
        sheet.write(rowx, 0, '', header_format)
        sheet.write(rowx, 1, '', header_format)
        for idx, year in enumerate(years):
            sheet.write(rowx, 2 + idx, f'FY {year}', header_format)
        rowx += 1

        # Data
        for group in grouped:
            start_row = rowx
            for sub_row in group['rows']:
                sheet.write(rowx, 1, sub_row['sub_bu'], text_format)
                for col_idx, amount in enumerate(sub_row['amounts']):
                    if amount:
                        sheet.write(rowx, 2 + col_idx, amount, number_format)
                    else:
                        sheet.write(rowx, 2 + col_idx, '-', empty_dash_format)
                rowx += 1

            end_row = rowx - 1
            if end_row > start_row:
                sheet.merge_range(start_row, 0, end_row, 0, group['partner_name'], text_format)
            else:
                sheet.write(start_row, 0, group['partner_name'], text_format)

            # Customer total
            sheet.merge_range(rowx, 0, rowx, 1, f"{group['partner_name']} Total", total_text_format)
            for col_idx, amount in enumerate(group['total']):
                if amount:
                    sheet.write(rowx, 2 + col_idx, amount, total_number_format)
                else:
                    sheet.write(rowx, 2 + col_idx, '-', empty_dash_format)
            rowx += 1

        # Grand Sub Total
        sheet.merge_range(rowx, 0, rowx, 1, 'Sub Total', total_text_format)
        for col_idx, amount in enumerate(grand_total):
            if amount:
                sheet.write(rowx, 2 + col_idx, amount, total_number_format)
            else:
                sheet.write(rowx, 2 + col_idx, '-', empty_dash_format)

        sheet.set_column(0, 0, 28)
        sheet.set_column(1, 1, 18)
        for idx in range(len(years)):
            sheet.set_column(2 + idx, 2 + idx, 18)

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'Yearly_Revenue_Comparison_%s.xlsx' % (fields.Date.context_today(self))
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
