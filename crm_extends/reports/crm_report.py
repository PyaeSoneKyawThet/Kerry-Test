# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _

class CRMReport(models.Model):
    _name = "performance.qunatity.report"
    _description = 'Performance by Quantity Report'
    _auto = False
    
    user_id = fields.Many2one("res.users", string="Salesperson", readonly=True)
    hunting = fields.Float(string="Hunting", readonly=True)
    projected = fields.Float(string="Projected", readonly=True)
    awarded = fields.Float(string="Awarded", readonly=True)
    loss = fields.Float(string="Loss", readonly=True)
    convertion_rate = fields.Float(string="Convertion Rate", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'performance_qunatity_report')
        self._cr.execute("""
            CREATE or REPLACE view performance_qunatity_report as (
                WITH stage_counts AS (
                    SELECT
                        user_id,
                        SUM(CASE WHEN stage.sequence = 0 THEN 1 ELSE 0 END) AS hunting,
                        SUM(CASE WHEN stage.sequence = 2 THEN 1 ELSE 0 END) AS projected,
                        SUM(CASE WHEN stage.sequence = 3 THEN 1 ELSE 0 END) AS awarded
                    FROM crm_lead crm
                    JOIN crm_stage stage ON crm.stage_id = stage.id
                    WHERE crm.active = TRUE
                    GROUP BY user_id
                    )
                    SELECT
                    user_id AS id,
                    user_id AS user_id,
                    COALESCE(hunting, 0) AS hunting,
                    COALESCE(projected, 0) AS projected,
                    COALESCE(awarded, 0) AS awarded,
                    COALESCE(hunting, 0) - COALESCE(awarded, 0) AS loss,
                    CASE
                        WHEN COALESCE(projected, 0) = 0 THEN 0
                        ELSE ROUND((COALESCE(projected, 0) - COALESCE(awarded, 0)) / COALESCE(projected, 0), 2)
                    END AS convertion_rate
                    FROM stage_counts
                    ORDER BY user_id            
                );
        """)