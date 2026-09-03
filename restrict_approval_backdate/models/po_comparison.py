from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta

class POComparison(models.Model):
    _inherit = 'po.comparison'

    @api.constrains('date')
    def check_date(self):
        for rec in self:
            approval_date = datetime.strptime(rec.date.strftime('%Y-%m-%d'), '%Y-%m-%d').date()
            if not approval_date:
                continue
            today = fields.Date.today()
            company = self.env.company
            allowed_backdate = self.env.user.has_group('restrict_backdate.group_allowed_backdate_access')
            limit_day = company.backdate_limit_day or 0
            backdate_limit = today - relativedelta(days=limit_day)
            if approval_date < today and (not allowed_backdate or approval_date < backdate_limit):
                raise UserError(_('You are not allowed to do backdate transaction or your backdate is beyond limit!'))
