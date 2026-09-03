from datetime import date

from odoo import fields, models, api, _


class CustomerForecastRevenue(models.Model):
    _name = "customer.forecast.revenue"
    _description = "Forecast Revenue"

    user_id = fields.Many2one(
        'res.users',
        string="Salesperson",
        default=lambda self: self.env.user
    )
    customer_id = fields.Many2one(
        'res.partner',
        string="Customer"
    )
    name = fields.Char(string="Name", default="Forecasted Revenue")
    commodity = fields.Char(string="Commodity")
    parent_category_id = fields.Many2one(
        'product.category',
        string="BU",
        domain="[('parent_id', '=', False), ('child_id', '!=', False)]"
    )
    category_id = fields.Many2one(
        'product.category',
        string="Sub BU",
        domain="[('parent_id', '=', parent_category_id)]"
    )
    expected_revenue = fields.Monetary(
        string="Expected Revenue",
        currency_field='currency_id'
    )

    def _selection_f_year(self):
        current_year = date.today().year
        return [(str(year), str(year)) for year in range(current_year - 20, current_year + 21)]

    f_year = fields.Selection(
        selection=_selection_f_year,
        string="Year",
    )
    f_month = fields.Selection([
        ('1', 'Jan'),
        ('2', 'Feb'),
        ('3', 'Mar'),
        ('4', 'Apr'),
        ('5', 'May'),
        ('6', 'Jun'),
        ('7', 'Jul'),
        ('8', 'Aug'),
        ('9', 'Sep'),
        ('10', 'Oct'),
        ('11', 'Nov'),
        ('12', 'Dec'),
    ], string="Month")
    forecast_month = fields.Date(
        string="Forecast Month",
        compute='_compute_forecast_month',
        store=True,
    )
    forecast_month_str = fields.Char(
        string="Forecast Month",
        compute='_compute_forecast_month_str',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('f_year', 'f_month')
    def _compute_forecast_month(self):
        for rec in self:
            if rec.f_year and rec.f_month:
                rec.forecast_month = date(int(rec.f_year), int(rec.f_month), 1)
            else:
                rec.forecast_month = False

    @api.depends('f_year', 'f_month')
    def _compute_forecast_month_str(self):
        month_names = dict(self._fields['f_month'].selection)
        for rec in self:
            if rec.f_year and rec.f_month:
                rec.forecast_month_str = f"{rec.f_year} {month_names.get(rec.f_month) or ''}"
            else:
                rec.forecast_month_str = False

    def _auto_init(self):
        cr = self._cr
        cr.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'customer_forecast_revenue'
              AND column_name = 'forecast_month'
        """)
        has_forecast_month = bool(cr.fetchone())
        super()._auto_init()
        if has_forecast_month:
            cr.execute("""
                UPDATE customer_forecast_revenue
                   SET f_year = EXTRACT(YEAR FROM forecast_month)::integer::text,
                       f_month = EXTRACT(MONTH FROM forecast_month)::integer::text
                 WHERE forecast_month IS NOT NULL
                   AND (f_year IS NULL OR f_month IS NULL)
            """)
