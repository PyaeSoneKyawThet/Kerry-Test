# -*- coding: utf-8 -*-
# Part of Softhealer Technologies

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    backdate_limit_day = fields.Float("Backdate Limit Days")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    backdate_limit_day = fields.Float("Backdate Limit Days", related="company_id.backdate_limit_day", readonly=False)