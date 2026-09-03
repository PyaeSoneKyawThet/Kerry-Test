# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    staff_location_id = fields.Many2one('staff.location', string="Document Location")

