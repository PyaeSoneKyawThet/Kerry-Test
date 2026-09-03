from odoo import fields, models, api

class ResCompany(models.Model):
    _inherit = "res.company"   
    
    compute_crm_stage = fields.Boolean(string="Compute Stage Reason", default=False)
    crm_stage_reason_seq1 = fields.Char(compute="_compute_reason_stage", string='Reason Seq 1', store=True) 
    crm_stage_reason_seq2 = fields.Char(compute="_compute_reason_stage", string='Reason Seq 2', store=True) 
    crm_stage_reason_seq3 = fields.Char(compute="_compute_reason_stage", string='Reason Seq 3', store=True) 
    crm_stage_reason_seq4 = fields.Char(compute="_compute_reason_stage", string='Reason Seq 4', store=True) 
    
    @api.onchange('compute_crm_stage')
    @api.depends('compute_crm_stage')
    def _compute_reason_stage(self):
        for rec in self:
            rec.crm_stage_reason_seq1 = False
            rec.crm_stage_reason_seq2 = False
            rec.crm_stage_reason_seq3 = False
            rec.crm_stage_reason_seq4 = False
            if rec.compute_crm_stage:
                seq1 = self.env['crm.stage'].search([('sequence', '=', 0)], limit=1)
                seq2 = self.env['crm.stage'].search([('sequence', '=', 1)], limit=1)
                seq3 = self.env['crm.stage'].search([('sequence', '=', 2)], limit=1)
                seq4 = self.env['crm.stage'].search([('sequence', '=', 3)], limit=1)
                rec.crm_stage_reason_seq1 = seq1.name
                rec.crm_stage_reason_seq2 = seq2.name
                rec.crm_stage_reason_seq3 = seq3.name
                rec.crm_stage_reason_seq4 = seq4.name