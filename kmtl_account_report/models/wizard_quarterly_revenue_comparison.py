from odoo import models, fields, _
from datetime import date, datetime
from collections import defaultdict
from calendar import monthrange
import io
import base64
import json


QUARTER_DEFS = [
    (1, 'Q1', 'Jan-Mar', 1, 3),
    (2, 'Q2', 'Apr-Jun', 4, 6),
    (3, 'Q3', 'Jul-Sep', 7, 9),
    (4, 'Q4', 'Oct-Dec', 10, 12),
]


class KMTLQuarterlyRevenueComparisonWizard(models.TransientModel):
    _name = 'kmtl.quarterly.revenue.comparison'
    _description = 'Quarterly Revenue Comparison Report Wizard'

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

    def _quarter_end(self, year, month):
        return date(year, month, monthrange(year, month)[1])

    def _periods_between(self, start_date, end_date):
        """Return quarters that overlap the selected duration, grouped by year."""
        periods = []
        for year in range(start_date.year, end_date.year + 1):
            for q_num, q_label, month_label, start_month, end_month in QUARTER_DEFS:
                q_start = date(year, start_month, 1)
                q_end = self._quarter_end(year, end_month)
                if q_end < start_date or q_start > end_date:
                    continue
                periods.append({
                    'year': year,
                    'q_num': q_num,
                    'q_label': q_label,
                    'month_label': month_label,
                    'start': max(q_start, start_date),
                    'end': min(q_end, end_date),
                })
        return periods

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

    def _to_date(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return fields.Date.to_date(value)

    def _sql_partner_ids(self):
        if not self.partner_ids:
            return None
        partners = self.env['res.partner'].search([
            ('id', 'child_of', self.partner_ids.ids),
        ])
        return tuple(partners.ids) or (0,)

    def _period_index_for_date(self, aml_date, periods):
        aml_date = self._to_date(aml_date)
        if not aml_date:
            return None
        for idx, period in enumerate(periods):
            if period['start'] <= aml_date <= period['end']:
                return idx
        return None

    def _gather_data(self):
        self.ensure_one()
        start = self.date_from
        stop = self.date_to
        periods = self._periods_between(start, stop)
        company_ids = tuple(self.env.companies.ids) or (self.env.company.id,)
        sub_bu_ids = self._get_sub_bu_account_ids()

        partner_filter_sql = ''
        params = [start, stop, company_ids]
        partner_ids = self._sql_partner_ids()
        if partner_ids:
            partner_filter_sql = 'AND COALESCE(aml.partner_id, am.partner_id) IN %s'
            params.append(partner_ids)

        query = (
            "SELECT COALESCE(aml.partner_id, am.partner_id), aml.date, "
            "aml.credit, aml.debit, aml.analytic_distribution "
            "FROM account_move_line aml "
            "JOIN account_move am ON aml.move_id = am.id "
            "JOIN account_account a ON aml.account_id = a.id "
            "WHERE aml.date >= %s AND aml.date <= %s "
            "AND a.account_type = 'income' "
            "AND am.state = 'posted' "
            "AND COALESCE(aml.display_type, '') NOT IN ('line_section', 'line_note') "
            "AND aml.company_id IN %s "
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

        amounts = defaultdict(lambda: defaultdict(float))
        partner_ids_found = set()

        for partner_id, aml_date, credit, debit, distribution in rows:
            period_idx = self._period_index_for_date(aml_date, periods)
            if period_idx is None:
                continue
            sub_bu_name = self._get_sub_bu_name(distribution, sub_bu_ids, analytic_names)
            amount = float(credit or 0.0) - float(debit or 0.0)
            amounts[(partner_id or 0, sub_bu_name)][period_idx] += amount
            partner_ids_found.add(partner_id or 0)

        if self.partner_ids:
            partners = self.partner_ids.sorted(key=lambda p: p.name or '')
        else:
            found_ids = [pid for pid in partner_ids_found if pid]
            partners = self.env['res.partner'].browse(found_ids).sorted(
                key=lambda p: p.name or ''
            )

        grouped = []
        period_count = len(periods)
        for partner in partners:
            sub_bu_rows = []
            partner_keys = [
                (pid, sub_bu)
                for (pid, sub_bu) in amounts.keys()
                if pid == partner.id
            ]
            partner_keys.sort(key=lambda item: item[1] or '')
            for _pid, sub_bu in partner_keys:
                period_amounts = [amounts[(_pid, sub_bu)].get(idx, 0.0) for idx in range(period_count)]
                if any(period_amounts):
                    sub_bu_rows.append({
                        'sub_bu': sub_bu or '-',
                        'amounts': period_amounts,
                    })
            if not sub_bu_rows and self.partner_ids:
                sub_bu_rows.append({
                    'sub_bu': '-',
                    'amounts': [0.0] * period_count,
                })
            if sub_bu_rows:
                customer_total = [
                    sum(row['amounts'][idx] for row in sub_bu_rows)
                    for idx in range(period_count)
                ]
                grouped.append({
                    'partner_name': partner.name or '',
                    'rows': sub_bu_rows,
                    'total': customer_total,
                })

        if not self.partner_ids and 0 in partner_ids_found:
            none_keys = [(pid, sub_bu) for (pid, sub_bu) in amounts.keys() if not pid]
            none_keys.sort(key=lambda item: item[1] or '')
            sub_bu_rows = []
            for _pid, sub_bu in none_keys:
                period_amounts = [amounts[(_pid, sub_bu)].get(idx, 0.0) for idx in range(period_count)]
                if any(period_amounts):
                    sub_bu_rows.append({
                        'sub_bu': sub_bu or '-',
                        'amounts': period_amounts,
                    })
            if sub_bu_rows:
                customer_total = [
                    sum(row['amounts'][idx] for row in sub_bu_rows)
                    for idx in range(period_count)
                ]
                grouped.append({
                    'partner_name': _('None'),
                    'rows': sub_bu_rows,
                    'total': customer_total,
                })

        grand_total = [
            sum(group['total'][idx] for group in grouped)
            for idx in range(period_count)
        ]
        return periods, grouped, grand_total

    def _write_amount(self, sheet, rowx, colx, amount, number_format, empty_format):
        if amount:
            sheet.write(rowx, colx, amount, number_format)
        else:
            sheet.write(rowx, colx, '-', empty_format)

    def _write_percent(self, sheet, rowx, colx, row_total, grand_sum, percent_format, empty_format):
        if grand_sum:
            sheet.write(rowx, colx, row_total / grand_sum, percent_format)
        else:
            sheet.write(rowx, colx, '-', empty_format)

    def action_export_xlsx(self):
        self.ensure_one()
        periods, grouped, grand_total = self._gather_data()

        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Quarterly Revenue Comparison')

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
        percent_format = workbook.add_format({
            'border': 1, 'num_format': '0.00%', 'valign': 'vcenter', 'align': 'center',
        })
        total_percent_format = workbook.add_format({
            'bold': True, 'border': 1, 'num_format': '0.00%',
            'valign': 'vcenter', 'align': 'center',
        })

        rowx = 0
        sheet.write(rowx, 0, self.env.company.name or '', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Quarterly Revenue Comparison', title_format)
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

        period_count = len(periods)
        percent_col = 2 + period_count

        # Header row 1: Year groups
        sheet.write(rowx, 0, 'Customer Name', header_format)
        sheet.write(rowx, 1, 'Sub-BU', header_format)
        colx = 2
        year_start = 0
        while year_start < period_count:
            year = periods[year_start]['year']
            year_end = year_start
            while year_end + 1 < period_count and periods[year_end + 1]['year'] == year:
                year_end += 1
            start_col = 2 + year_start
            end_col = 2 + year_end
            if start_col == end_col:
                sheet.write(rowx, start_col, str(year), header_format)
            else:
                sheet.merge_range(rowx, start_col, rowx, end_col, str(year), header_format)
            year_start = year_end + 1
        sheet.write(rowx, percent_col, '%', header_format)
        rowx += 1

        # Header row 2: month ranges
        sheet.write(rowx, 0, '', header_format)
        sheet.write(rowx, 1, '', header_format)
        for idx, period in enumerate(periods):
            sheet.write(rowx, 2 + idx, period['month_label'], header_format)
        sheet.write(rowx, percent_col, '', header_format)
        rowx += 1

        # Header row 3: quarter labels
        sheet.write(rowx, 0, '', header_format)
        sheet.write(rowx, 1, '', header_format)
        for idx, period in enumerate(periods):
            sheet.write(rowx, 2 + idx, period['q_label'], header_format)
        sheet.write(rowx, percent_col, '%', header_format)
        rowx += 1

        grand_sum = sum(grand_total)

        for group in grouped:
            start_row = rowx
            for sub_row in group['rows']:
                sheet.write(rowx, 1, sub_row['sub_bu'], text_format)
                for col_idx, amount in enumerate(sub_row['amounts']):
                    self._write_amount(sheet, rowx, 2 + col_idx, amount, number_format, empty_dash_format)
                self._write_percent(
                    sheet, rowx, percent_col, sum(sub_row['amounts']), grand_sum,
                    percent_format, empty_dash_format,
                )
                rowx += 1

            end_row = rowx - 1
            if end_row > start_row:
                sheet.merge_range(start_row, 0, end_row, 0, group['partner_name'], text_format)
            else:
                sheet.write(start_row, 0, group['partner_name'], text_format)

            sheet.merge_range(rowx, 0, rowx, 1, f"{group['partner_name']} Total", total_text_format)
            for col_idx, amount in enumerate(group['total']):
                self._write_amount(sheet, rowx, 2 + col_idx, amount, total_number_format, empty_dash_format)
            self._write_percent(
                sheet, rowx, percent_col, sum(group['total']), grand_sum,
                total_percent_format, empty_dash_format,
            )
            rowx += 1

        sheet.merge_range(rowx, 0, rowx, 1, 'Sub Total', total_text_format)
        for col_idx, amount in enumerate(grand_total):
            self._write_amount(sheet, rowx, 2 + col_idx, amount, total_number_format, empty_dash_format)
        self._write_percent(
            sheet, rowx, percent_col, grand_sum, grand_sum,
            total_percent_format, empty_dash_format,
        )

        sheet.set_column(0, 0, 28)
        sheet.set_column(1, 1, 18)
        for idx in range(period_count):
            sheet.set_column(2 + idx, 2 + idx, 14)
        sheet.set_column(percent_col, percent_col, 12)

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'Quarterly_Revenue_Comparison_%s.xlsx' % (fields.Date.context_today(self))
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
