from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError

class AccountMoveLine(models.Model):     
    _inherit = "account.move.line" 

    business_name = fields.Char(string="Business Name", compute="_compute_business_name", store=True)
    plan_2 = fields.Char(string="BU", compute="_compute_plan", store=True)
    plan_3 = fields.Char(string="Sub BU", compute="_compute_plan", store=True)
    plan_4 = fields.Char(string="Job Location", compute="_compute_plan", store=True)
    plan_5 = fields.Char(string="Job Department", compute="_compute_plan", store=True)

    @api.depends('account_id','analytic_distribution')
    def _compute_business_name(self):
        for line in self:
            account_name = f"{line.account_id.code} {line.account_id.name}"
            if line.analytic_distribution:
                analytic_account_ids = list({int(account_id) for account_id in ",".join(line.analytic_distribution.keys()).split(",")})
                records = self.env['account.analytic.account'].search(
                            [('id', 'in', analytic_account_ids)],
                            order='plan_id asc'
                        )
                location_names = " * ".join((records.filtered(lambda a: a.plan_id and a.plan_id.name.lower() != 'projects')).mapped('name'))
                if location_names:
                    line.business_name = f"{account_name} * {location_names}"
                else:
                    line.business_name = f"{account_name}"
            else:
                line.business_name = account_name
    
    @api.depends('account_id','analytic_distribution')
    def _compute_plan(self):
        for line in self:
            if line.analytic_distribution:
                analytic_account_ids = list({int(account_id) for account_id in ",".join(line.analytic_distribution.keys()).split(",")})
                records = self.env['account.analytic.account'].search(
                            [('id', 'in', analytic_account_ids)],
                        )
                plan_2 = records.filtered(lambda a: a.plan_id.id == 2).mapped('name')
                plan_3 = records.filtered(lambda a: a.plan_id.id == 3).mapped('name')
                plan_4 = records.filtered(lambda a: a.plan_id.id == 4).mapped('name')
                plan_5 = records.filtered(lambda a: a.plan_id.id == 5).mapped('name')

                line.plan_2 = plan_2[0] if plan_2 else ''
                line.plan_3 = plan_3[0] if plan_3 else ''
                line.plan_4 = plan_4[0] if plan_4 else ''
                line.plan_5 = plan_5[0] if plan_5 else ''

            else:
                line.plan_2 = line.plan_3 = line.plan_4 = line.plan_5 = ''
            
            