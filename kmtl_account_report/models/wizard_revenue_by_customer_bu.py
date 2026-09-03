from odoo import models, fields, _
from collections import defaultdict, OrderedDict
import io
import base64
import json


class KMTLRevenueByCustomerBUWizard(models.TransientModel):
    _name = 'kmtl.revenue.by.customer.bu'
    _description = 'Revenue by Customer/BU Report Wizard'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    bu_id = fields.Many2one(
        'account.analytic.account',
        string='Business Unit',
        required=True,
        domain="[('plan_id.is_bu', '=', True)]",
    )
    partner_ids = fields.Many2many('res.partner', string='Customers')
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _format_duration_date(self, value, with_day=True):
        if not value:
            return ''
        if with_day:
            return f"{value.day} {value.strftime('%b %Y')}"
        return value.strftime('%b %Y')

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
            return 'None'
        return analytic_names.get(matched[0], 'None')

    def _line_has_bu(self, analytic_distribution, bu_id):
        return bu_id in self._get_analytic_ids_from_distribution(analytic_distribution)

    def _sql_partner_ids(self):
        if not self.partner_ids:
            return None
        partners = self.env['res.partner'].search([
            ('id', 'child_of', self.partner_ids.ids),
        ])
        return tuple(partners.ids) or (0,)

    def _gather_data(self):
        self.ensure_one()
        start = self.date_from
        stop = self.date_to
        company_ids = tuple(self.env.companies.ids) or (self.env.company.id,)
        bu_id = self.bu_id.id
        sub_bu_ids = self._get_sub_bu_account_ids()

        partner_filter_sql = ''
        params = [start, stop, company_ids]
        partner_ids = self._sql_partner_ids()
        if partner_ids:
            partner_filter_sql = 'AND COALESCE(aml.partner_id, am.partner_id) IN %s'
            params.append(partner_ids)

        query = (
            "SELECT COALESCE(aml.partner_id, am.partner_id), "
            "aml.credit, aml.debit, aml.analytic_distribution "
            "FROM account_move_line aml "
            "JOIN account_move am ON aml.move_id = am.id "
            "JOIN account_account a ON aml.account_id = a.id "
            "WHERE aml.date >= %s AND aml.date <= %s "
            "AND a.account_type IN ('income', 'income_other') "
            "AND am.state = 'posted' "
            "AND COALESCE(aml.display_type, '') NOT IN ('line_section', 'line_note') "
            "AND aml.company_id IN %s "
            + partner_filter_sql
        )
        self.env.cr.execute(query, tuple(params))
        rows = self.env.cr.fetchall()

        all_analytic_ids = set()
        for _partner_id, _credit, _debit, distribution in rows:
            all_analytic_ids |= self._get_analytic_ids_from_distribution(distribution)
        analytic_names = {
            rec.id: rec.name
            for rec in self.env['account.analytic.account'].browse(list(all_analytic_ids))
        }

        # amounts[partner_id][sub_bu_name] = amount
        amounts = defaultdict(lambda: defaultdict(float))
        sub_bu_columns = OrderedDict()
        partner_ids_found = set()

        for partner_id, credit, debit, distribution in rows:
            if not self._line_has_bu(distribution, bu_id):
                continue
            partner_id = partner_id or 0
            sub_bu_name = self._get_sub_bu_name(distribution, sub_bu_ids, analytic_names)
            amount = float(credit or 0.0) - float(debit or 0.0)
            amounts[partner_id][sub_bu_name] += amount
            partner_ids_found.add(partner_id)
            if sub_bu_name not in sub_bu_columns:
                sub_bu_columns[sub_bu_name] = True

        # Keep Sub-BU names sorted; put None last
        ordered_sub_bus = sorted(
            [name for name in sub_bu_columns if name != 'None'],
            key=lambda n: n.lower(),
        )
        if 'None' in sub_bu_columns:
            ordered_sub_bus.append('None')

        if self.partner_ids:
            partners = self.partner_ids.sorted(key=lambda p: p.name or '')
        else:
            found_ids = [pid for pid in partner_ids_found if pid]
            partners = self.env['res.partner'].browse(found_ids).sorted(
                key=lambda p: p.name or ''
            )

        data_rows = []
        for partner in partners:
            sub_amounts = [
                amounts[partner.id].get(sub_bu, 0.0)
                for sub_bu in ordered_sub_bus
            ]
            if not any(sub_amounts) and not self.partner_ids:
                continue
            if not ordered_sub_bus and not amounts[partner.id]:
                continue
            # Selected customers with no matching lines still show empty
            if not ordered_sub_bus and self.partner_ids:
                data_rows.append({
                    'name': partner.name or '',
                    'amounts': [],
                    'total': 0.0,
                })
                continue
            if not any(sub_amounts) and self.partner_ids:
                data_rows.append({
                    'name': partner.name or '',
                    'amounts': [0.0] * len(ordered_sub_bus),
                    'total': 0.0,
                })
                continue
            if any(sub_amounts) or self.partner_ids:
                data_rows.append({
                    'name': partner.name or '',
                    'amounts': sub_amounts,
                    'total': sum(sub_amounts),
                })

        if not self.partner_ids and 0 in partner_ids_found:
            sub_amounts = [
                amounts[0].get(sub_bu, 0.0)
                for sub_bu in ordered_sub_bus
            ]
            if any(sub_amounts):
                data_rows.append({
                    'name': _('None'),
                    'amounts': sub_amounts,
                    'total': sum(sub_amounts),
                })

        column_totals = [
            sum(row['amounts'][idx] for row in data_rows if row['amounts'])
            for idx in range(len(ordered_sub_bus))
        ]
        grand_total = sum(row['total'] for row in data_rows)
        return ordered_sub_bus, data_rows, column_totals, grand_total

    def _write_amount(self, sheet, rowx, colx, amount, number_format, empty_format):
        if amount:
            sheet.write(rowx, colx, amount, number_format)
        else:
            sheet.write(rowx, colx, '-', empty_format)

    def action_export_xlsx(self):
        self.ensure_one()
        sub_bus, data_rows, column_totals, grand_total = self._gather_data()

        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Revenue by Customer BU')

        title_format = workbook.add_format({'bold': True, 'font_size': 12})
        header_format = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
        })
        text_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        number_format = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00', 'valign': 'vcenter',
        })
        total_text_format = workbook.add_format({
            'bold': True, 'border': 1, 'valign': 'vcenter',
        })
        total_number_format = workbook.add_format({
            'bold': True, 'border': 1, 'num_format': '#,##0.00', 'valign': 'vcenter',
        })
        empty_dash_format = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
        })

        rowx = 0
        sheet.write(rowx, 0, self.env.company.name or '', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Revenue by Customer/BU', title_format)
        rowx += 1
        sheet.write(rowx, 0, f'Business Unit : {self.bu_id.name or ""}', title_format)
        rowx += 1
        duration = (
            f"Duration : From {self._format_duration_date(self.date_from, with_day=True)} "
            f"To {self._format_duration_date(self.date_to, with_day=True)}"
        )
        sheet.write(rowx, 0, duration, title_format)
        rowx += 1
        currency_name = self.env.company.currency_id.name or 'MMK'
        sheet.write(rowx, 0, f'Currency : {currency_name}', title_format)
        rowx += 2

        # Header row 1
        sheet.write(rowx, 0, 'No', header_format)
        sheet.write(rowx, 1, 'Customer Name', header_format)
        total_col = 2 + len(sub_bus)
        if sub_bus:
            if len(sub_bus) == 1:
                sheet.write(rowx, 2, 'Sub BU', header_format)
            else:
                sheet.merge_range(rowx, 2, rowx, total_col - 1, 'Sub BU', header_format)
        sheet.write(rowx, total_col, 'Total', header_format)
        rowx += 1

        # Header row 2: Sub-BU names
        sheet.write(rowx, 0, '', header_format)
        sheet.write(rowx, 1, '', header_format)
        for idx, sub_bu in enumerate(sub_bus):
            sheet.write(rowx, 2 + idx, sub_bu, header_format)
        sheet.write(rowx, total_col, '', header_format)
        rowx += 1

        for no, row in enumerate(data_rows, start=1):
            sheet.write(rowx, 0, no, text_format)
            sheet.write(rowx, 1, row['name'], text_format)
            for col_idx, amount in enumerate(row['amounts']):
                self._write_amount(sheet, rowx, 2 + col_idx, amount, number_format, empty_dash_format)
            if not row['amounts'] and sub_bus:
                for col_idx in range(len(sub_bus)):
                    sheet.write(rowx, 2 + col_idx, '-', empty_dash_format)
            self._write_amount(sheet, rowx, total_col, row['total'], number_format, empty_dash_format)
            rowx += 1

        # Totals
        sheet.write(rowx, 0, '', total_text_format)
        sheet.write(rowx, 1, 'Total', total_text_format)
        for col_idx, amount in enumerate(column_totals):
            self._write_amount(sheet, rowx, 2 + col_idx, amount, total_number_format, empty_dash_format)
        self._write_amount(sheet, rowx, total_col, grand_total, total_number_format, empty_dash_format)

        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 1, 30)
        for idx in range(len(sub_bus)):
            sheet.set_column(2 + idx, 2 + idx, 18)
        sheet.set_column(total_col, total_col, 16)

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'Revenue_by_Customer_BU_%s.xlsx' % (fields.Date.context_today(self))
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
