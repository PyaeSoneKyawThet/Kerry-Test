from odoo import models, fields, api, _
from odoo.osv import expression
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import io
import base64


class SaleForecastReportWizard(models.TransientModel):
    _name = 'sale.forecast.report.wizard'
    _description = 'Sale Forecast Report Wizard'

    as_of_date = fields.Date(string="As Of Date", required=True, default=fields.Date.context_today)
    fc_months = fields.Selection([
        ('3', '3 months'),
        ('6', '6 months'),
        ('12', '12 months'),
    ], string="FC Months", required=True, default='3')
    
    parent_category_id = fields.Many2one(
        'product.category',
        string="BU",
        domain="[('parent_id', '=', False), ('child_id', '!=', False)]",
    )
    category_id = fields.Many2one('product.category', string="Sub BU", domain="[('parent_id', '=', parent_category_id)]")
    sale_pic_ids = fields.Many2many(
        'res.users',
        string="Salesperson",
        domain=lambda self: self._get_sale_person_domain(),
    )
    currency_id = fields.Many2one('res.currency', string="Currency")
    
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _get_sale_person_domain(self):
        current_user = self.env.user
        if current_user.has_group('sales_team.group_sale_manager'):
            partners = self.env['res.partner'].search([])
            users = partners.mapped('sale_pic_ids')
            return [('id', 'in', users.ids)]
        return [('id', '=', current_user.id)]

    def _gather_data(self):
        self.ensure_one()
        start = self.as_of_date
        num_months = int(self.fc_months)
        company = self.env.company
        target_currency = self.currency_id or company.currency_id
        
        periods = []
        cur = start
        for i in range(num_months):
            if i == 0:
                s = cur
                e = date(s.year, s.month, 1) + relativedelta(months=1) - timedelta(days=1)
            else:
                s = date(cur.year, cur.month, 1)
                e = s + relativedelta(months=1) - timedelta(days=1)
            
            label = s.strftime('%b %y')
            periods.append((label, s, e))
            cur = e + timedelta(days=1)
        
        end_date = periods[-1][2]
        results = {}

        def _add_to_results(user, customer, commodity, bu, sub_bu, date_ref, amount, currency):
            key = (user.name or '', customer.name or '', commodity or '', bu.name or '', sub_bu.name or '')
            if key not in results:
                results[key] = [0.0] * num_months
            
            # Convert currency
            if currency and currency != target_currency:
                amount = currency._convert(amount, target_currency, company, self.as_of_date)
            
            # Find period
            for idx, (_, pstart, pend) in enumerate(periods):
                if pstart <= date_ref <= pend:
                    results[key][idx] += amount
                    break
        
        # Data Source 1: crm.lead
        ds1_domain = [
            ('stage_id.name', '=', 'Projected (Proposition)'),
            ('probability', '>=', 80),
            ('active', '=', True),
            ('date_deadline', '>=', start),
            ('date_deadline', '<=', end_date)
        ]
        if self.parent_category_id:
            ds1_domain.append(('category_id.parent_id', '=', self.parent_category_id.id))
        if self.category_id:
            ds1_domain.append(('category_id', '=', self.category_id.id))
        if self.sale_pic_ids:
            ds1_domain.append(('user_id', 'in', self.sale_pic_ids.ids))
            
        leads = self.env['crm.lead'].search(ds1_domain)
        for lead in leads:
            _add_to_results(
                lead.user_id,
                lead.partner_id,
                lead.commodity,
                lead.category_id.parent_id,
                lead.category_id,
                lead.date_deadline,
                lead.expected_revenue,
                lead.currency_id or lead.company_currency
            )
            
        # Data Source 2: customer.forecast.revenue
        ds2_domain = []
        period_domains = [
            [('f_year', '=', str(s.year)), ('f_month', '=', str(s.month))]
            for _, s, _e in periods
        ]
        if period_domains:
            ds2_domain = expression.OR(period_domains)
        if self.parent_category_id:
            ds2_domain = expression.AND([ds2_domain, [('parent_category_id', '=', self.parent_category_id.id)]])
        if self.category_id:
            ds2_domain = expression.AND([ds2_domain, [('category_id', '=', self.category_id.id)]])
        if self.sale_pic_ids:
            ds2_domain = expression.AND([ds2_domain, [('user_id', 'in', self.sale_pic_ids.ids)]])
            
        forecasts = self.env['customer.forecast.revenue'].search(ds2_domain)
        for forecast in forecasts:
            if forecast.f_year and forecast.f_month:
                f_year = int(forecast.f_year)
                f_month = int(forecast.f_month)
                for idx, (_, pstart, pend) in enumerate(periods):
                    if pstart.year == f_year and pstart.month == f_month:
                        key = (
                            forecast.user_id.name or '',
                            forecast.customer_id.name or '',
                            forecast.commodity or '',
                            forecast.parent_category_id.name or '',
                            forecast.category_id.name or ''
                        )
                        if key not in results:
                            results[key] = [0.0] * num_months
                        
                        amount = forecast.expected_revenue
                        currency = forecast.currency_id or company.currency_id
                        if currency and currency != target_currency:
                            amount = currency._convert(amount, target_currency, company, self.as_of_date)
                            
                        results[key][idx] += amount
                        break
                        
        return periods, results, end_date

    def action_print(self):
        self.ensure_one()
        periods, data, end_date = self._gather_data()
        
        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Sale Forecast Report')

        # Formats
        title_format = workbook.add_format({'bold': True, 'font_size': 12})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        default_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        
        # Set column widths
        sheet.set_column(0, 0, 5)   # No
        sheet.set_column(1, 1, 25)  # Sale Person
        sheet.set_column(2, 2, 25)  # Customer
        sheet.set_column(3, 3, 20)  # Commodity
        sheet.set_column(4, 5, 20)  # BU, Sub BU
        sheet.set_column(6, 6 + len(periods) - 1, 18)  # FC Months
        
        sheet.write(0, 0, 'KM Terminal and Logistics Limited', title_format)
        sheet.write(1, 0, 'Sale Forecast Report/Template', title_format)
        
        # Duration format: 20.7.2026
        as_of_str = self.as_of_date.strftime('%d.%m.%Y')
        as_of_str = as_of_str.replace('.0', '.') if as_of_str.startswith('0') else as_of_str.lstrip('0')
        end_str = end_date.strftime('%d.%m.%Y')
        end_str = end_str.replace('.0', '.') if end_str.startswith('0') else end_str.lstrip('0')
        
        duration_text = f"Duration : {as_of_str} / {end_str}"
        fc_text = f"FC month: {self.fc_months} months"
        currency_text = f"Currency: {self.currency_id.name if self.currency_id else self.env.company.currency_id.name}"
        sheet.write(2, 0, duration_text, title_format)
        sheet.write(2, 2, fc_text, title_format)
        sheet.write(2, 4, currency_text, title_format)
        
        rowx = 4
        # Columns
        headers = ['No', 'Sale Person', 'Customer', 'Commodity', 'BU', 'Sub BU']
        
        # Write first level header for FC Month
        if len(periods) > 1:
            sheet.merge_range(rowx, len(headers), rowx, len(headers) + len(periods) - 1, 'FC Month', header_format)
        else:
            sheet.write(rowx, len(headers), 'FC Month', header_format)
            
        rowx += 1
        for idx, h in enumerate(headers):
            sheet.write(rowx, idx, h, header_format)
            
        colx = len(headers)
        for label, _, _ in periods:
            sheet.write(rowx, colx, label, header_format)
            colx += 1
            
        rowx += 1
        
        # Write data
        no = 1
        for key, values in data.items():
            sheet.write(rowx, 0, no, text_format)
            sheet.write(rowx, 1, key[0], text_format)
            sheet.write(rowx, 2, key[1], text_format)
            sheet.write(rowx, 3, key[2], text_format)
            sheet.write(rowx, 4, key[3], text_format)
            sheet.write(rowx, 5, key[4], text_format)

            colx = 6
            for val in values:
                sheet.write(rowx, colx, val, default_format)
                colx += 1
            rowx += 1
            no += 1
            
        workbook.close()
        output.seek(0)
        file_data = output.read()

        fname = f"Sale Forecast Report({fields.Date.context_today(self)}).xlsx"
        self.write({
            'excel_file': base64.b64encode(file_data),
            'file_name': fname,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
