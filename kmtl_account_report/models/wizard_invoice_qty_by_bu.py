from odoo import models, fields, _
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import io
import base64
import json


class KMTLInvoiceQtyByBUWizard(models.TransientModel):
    _name = 'kmtl.invoice.qty.by.bu'
    _description = 'Invoice Qty by BU Report Wizard'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    group_by = fields.Selection([
        ('year', 'Year'),
        ('quarter', 'Quarter'),
        ('month', 'Month'),
        ('week', 'Week'),
        ('day', 'Day'),
    ], string='Date Group By', required=True, default='week')
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _format_duration_date(self, value):
        if not value:
            return ''
        return f"{value.day} {value.strftime('%B %Y')}"

    def _periods_between(self, start_date, end_date, group_by):
        """Build periods. Quarter/Week/Month/Day number from 1 within the selected range."""
        periods = []
        if group_by == 'year':
            year = start_date.year
            while year <= end_date.year:
                s = date(year, 1, 1)
                e = date(year, 12, 31)
                periods.append((str(year), max(s, start_date), min(e, end_date)))
                year += 1
        elif group_by == 'quarter':
            # Sequential quarters from start_date (Quarter 1, Quarter 2, ...)
            cur = start_date
            q_no = 1
            while cur <= end_date:
                s = cur
                e = min(s + relativedelta(months=3) - timedelta(days=1), end_date)
                periods.append((f'Quarter {q_no}', s, e))
                cur = e + timedelta(days=1)
                q_no += 1
        elif group_by == 'month':
            cur = date(start_date.year, start_date.month, 1)
            m_no = 1
            while cur <= end_date:
                s = max(cur, start_date)
                e = min(cur + relativedelta(months=1) - timedelta(days=1), end_date)
                periods.append((f'Month {m_no}', s, e))
                cur = cur + relativedelta(months=1)
                m_no += 1
        elif group_by == 'week':
            cur = start_date
            w_no = 1
            while cur <= end_date:
                s = cur
                e = min(cur + timedelta(days=6), end_date)
                periods.append((f'Week {w_no}', s, e))
                cur = e + timedelta(days=1)
                w_no += 1
        else:  # day
            cur = start_date
            d_no = 1
            while cur <= end_date:
                periods.append((f'Day {d_no}', cur, cur))
                cur = cur + timedelta(days=1)
                d_no += 1
        return periods

    def _get_bu_accounts(self):
        AnalyticAccount = self.env['account.analytic.account']
        Plan = self.env['account.analytic.plan']
        if 'is_bu' in Plan._fields:
            return AnalyticAccount.search([('plan_id.is_bu', '=', True)], order='name')
        return AnalyticAccount.search([('plan_id.name', 'ilike', 'bu')], order='name')

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

    def _period_index_for_date(self, aml_date, periods):
        if not aml_date:
            return None
        if not isinstance(aml_date, date):
            aml_date = fields.Date.to_date(aml_date)
        for idx, (_label, pstart, pend) in enumerate(periods):
            if pstart <= aml_date <= pend:
                return idx
        return None

    def _gather_data(self):
        self.ensure_one()
        start = self.date_from
        stop = self.date_to
        periods = self._periods_between(start, stop, self.group_by)
        company_ids = tuple(self.env.companies.ids) or (self.env.company.id,)
        bu_accounts = self._get_bu_accounts()
        bu_ids = set(bu_accounts.ids)

        query = (
            "SELECT am.id, aml.date, aml.balance, aml.analytic_distribution "
            "FROM account_move_line aml "
            "JOIN account_move am ON aml.move_id = am.id "
            "WHERE aml.date >= %s AND aml.date <= %s "
            "AND am.move_type IN ('out_invoice', 'out_refund') "
            "AND am.state = 'posted' "
            "AND COALESCE(aml.display_type, '') NOT IN ('line_section', 'line_note') "
            "AND aml.company_id IN %s "
            "AND aml.analytic_distribution IS NOT NULL "
        )
        self.env.cr.execute(query, (start, stop, company_ids))
        rows = self.env.cr.fetchall()

        # qty: distinct move ids per (bu_id, period_idx)
        # amount: sum of company-currency signed amount per (bu_id, period_idx)
        qty_moves = defaultdict(lambda: defaultdict(set))
        amounts = defaultdict(lambda: defaultdict(float))

        for move_id, aml_date, balance, distribution in rows:
            period_idx = self._period_index_for_date(aml_date, periods)
            if period_idx is None:
                continue
            line_analytic_ids = self._get_analytic_ids_from_distribution(distribution)
            matched_bu_ids = line_analytic_ids & bu_ids
            if not matched_bu_ids:
                continue
            # balance is company currency; for invoices income is usually negative balance
            # show revenue as positive: -balance (out_invoice), refunds reverse naturally
            amount = -float(balance or 0.0)
            for bu_id in matched_bu_ids:
                qty_moves[bu_id][period_idx].add(move_id)
                amounts[bu_id][period_idx] += amount

        data_rows = []
        for bu in bu_accounts:
            period_qtys = []
            period_amts = []
            for idx in range(len(periods)):
                period_qtys.append(float(len(qty_moves[bu.id][idx])))
                period_amts.append(amounts[bu.id][idx])
            data_rows.append({
                'name': bu.name or '',
                'qtys': period_qtys,
                'amounts': period_amts,
            })

        return periods, data_rows

    def action_export_xlsx(self):
        self.ensure_one()
        periods, data_rows = self._gather_data()

        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Invoice Qty by BU')

        title_format = workbook.add_format({'bold': True, 'font_size': 12})
        header_format = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D9D9D9',
        })
        text_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        number_format = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00', 'valign': 'vcenter',
        })
        empty_format = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
        })

        rowx = 0
        sheet.write(rowx, 0, self.env.company.name or '', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Invoice Qty by BU', title_format)
        rowx += 1
        duration = (
            f"Duration : From {self._format_duration_date(self.date_from)} "
            f"To {self._format_duration_date(self.date_to)}"
        )
        sheet.write(rowx, 0, duration, title_format)
        rowx += 1
        currency_name = self.env.company.currency_id.name or 'MMK'
        sheet.write(rowx, 0, f'Currency : {currency_name}', title_format)
        rowx += 2

        # Header row 1: No / Business Unit / period group labels
        sheet.merge_range(rowx, 0, rowx + 1, 0, 'No', header_format)
        sheet.merge_range(rowx, 1, rowx + 1, 1, 'Business Unit', header_format)
        for idx, (label, _s, _e) in enumerate(periods):
            start_col = 2 + idx * 2
            end_col = start_col + 1
            sheet.merge_range(rowx, start_col, rowx, end_col, label, header_format)
        rowx += 1

        # Header row 2: QTY / Amount under each period
        for idx in range(len(periods)):
            start_col = 2 + idx * 2
            sheet.write(rowx, start_col, 'QTY', header_format)
            sheet.write(rowx, start_col + 1, 'Amount', header_format)
        rowx += 1

        for no, row in enumerate(data_rows, start=1):
            sheet.write(rowx, 0, no, text_format)
            sheet.write(rowx, 1, row['name'], text_format)
            for idx in range(len(periods)):
                qty = row['qtys'][idx]
                amt = row['amounts'][idx]
                col = 2 + idx * 2
                if qty:
                    sheet.write(rowx, col, qty, number_format)
                else:
                    sheet.write(rowx, col, '', empty_format)
                if amt:
                    sheet.write(rowx, col + 1, amt, number_format)
                else:
                    sheet.write(rowx, col + 1, '', empty_format)
            rowx += 1

        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 1, 22)
        for idx in range(len(periods)):
            col = 2 + idx * 2
            sheet.set_column(col, col, 10)
            sheet.set_column(col + 1, col + 1, 16)

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'Invoice_Qty_by_BU_%s.xlsx' % (fields.Date.context_today(self))
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
