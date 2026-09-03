from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.constrains('date_order')
    def check_date_order(self):
        for order in self:
            order_date = datetime.strptime(order.date_order.strftime('%Y-%m-%d'), '%Y-%m-%d').date()
            if not order_date:
                continue
            today = fields.Date.today()
            company = self.env.company
            allowed_backdate = self.env.user.has_group('restrict_backdate.group_allowed_backdate_access')
            limit_day = company.backdate_limit_day or 0
            backdate_limit = today - relativedelta(days=limit_day)
            if order_date < today and (not allowed_backdate or order_date < backdate_limit):
                raise UserError(_('You are not allowed to do backdate transaction or your backdate is beyond limit!'))
