# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    is_bu = fields.Boolean(string='Is BU')
    is_sub_bu = fields.Boolean(string='Is Sub BU')
