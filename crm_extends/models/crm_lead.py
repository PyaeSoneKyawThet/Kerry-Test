from odoo import fields, models, api, tools, _
from lxml import etree
from odoo.exceptions import UserError
from datetime import date,timedelta

class CrmLead(models.Model): 
    _inherit = "crm.lead"
    _rec_name = 'crm_ref'    

    date_deadline = fields.Date('Go Live Date', help="Estimate of the date on which the opportunity will be won.")
    currency_id = fields.Many2one('res.currency', string='Manual Currency')
    crm_ref = fields.Char("Reference")
    so_ids = fields.Many2many('sale.order', string="Quotaions", copy=False)
    category_id = fields.Many2one('product.category', domain= "[('parent_id', '!=', False), ('show_in_quotation', '!=', False)]", string='BU/Sub Service')
    industry_id = fields.Many2one('crm.industry',string="Industry")
    commodity = fields.Char(string="Commodity")
    volume = fields.Char(string="Volume")
    volume_rev = fields.Char(string="Volume & Rev")
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms")
    stage_seq =  fields.Integer(related="stage_id.sequence", string="Stage Seq")
    reason_seq1 = fields.Char(string="Reason 1", tracking=True)
    reason_seq2 = fields.Char(string="Reason 2", tracking=True)
    reason_seq3 = fields.Char(string="Reason 3", tracking=True)
    reason_seq4 = fields.Char(string="Reason 4", tracking=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    unit_id = fields.Many2one('crm.unit', string='Unit')
    uom_category_id = fields.Many2one('uom.category', string="UoM Category", related="uom_id.category_id", store=True)
    product_id = fields.Many2one('product.product', string='Product')
    load_type = fields.Selection([
        ('none', ''),
        ('front_load', 'Front Load'),
        ('back_load', 'Back Load'),
    ], string='Load Type', default='none')
    is_won_stage = fields.Boolean(compute='_compute_is_won_stage', store=False)
    date_seq1 = fields.Date(string="Date 1", default=fields.Date.today(), tracking=True, copy=False)
    date_seq2 = fields.Date(string="Date 2", tracking=True)
    date_seq3 = fields.Date(string="Date 3", tracking=True)
    date_seq4 = fields.Date(string="Date 4", tracking=True)
    follow_up_state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
    ], string='Follow-up Stage', default='draft')
    lost_date = fields.Date(string="Lost Date", tracking=True, copy=False)

    @api.depends('stage_id')
    def _compute_is_won_stage(self):
        for lead in self:
            lead.is_won_stage = lead.stage_id.is_won
    
    #OVERRIDE        
    @api.depends('probability', 'automated_probability')
    def _compute_is_automated_probability(self):
        """ If probability and automated_probability are equal probability computation
        is considered as automatic, aka probability is sync with automated_probability """
        for lead in self:
            lead.is_automated_probability = tools.float_compare(lead.probability, lead.automated_probability, 2) == 0 and False
    
    def _check_expected_revenue(self, vals):
        stage_id = vals.get('stage_id', self.stage_id.id)
        stage_seq = vals.get('stage_seq', self.stage_seq)
        reason_seq2 = vals.get('reason_seq2', self.reason_seq2)
        reason_seq3 = vals.get('reason_seq3', self.reason_seq3)
        expected_revenue = vals.get('expected_revenue', self.expected_revenue)
        if stage_id:
            stage = self.env['crm.stage'].browse(stage_id)
            if stage.sequence == 2 and expected_revenue == 0:
                raise UserError("You need to fill in the Expected Revenue for this stage.")
        if stage_seq == 1 and reason_seq2 == False:
            raise UserError("You need to fill in the Reason 2 for this stage.")
        if stage_seq == 2 and reason_seq3 == False:
            raise UserError("You need to fill in the Reason 3 for this stage.")
            
    def write(self, vals):
        if self.stage_id.is_won:
            allowed_fields = {'reason_seq1', 'reason_seq2', 'reason_seq3', 'reason_seq4', 'description', 'so_ids'}
            restricted_fields = set(vals.keys()) - allowed_fields
            if restricted_fields:
                raise UserError("You cannot modify fields after the CRM stage is 'won', except for Reason and Internal Note.")
            if 'stage_id' in vals and vals['stage_id'] != self.stage_id.id:
                raise UserError("You cannot change the stage after it has been marked as 'won'.")

        now = self.env.cr.now()
        if 'stage_id' in vals:
            new_stage_id = vals['stage_id']
            current_stage_id = self.stage_id.id
            new_stage = self.env['crm.stage'].browse(vals['stage_id'])
            
            if current_stage_id == 1 and new_stage_id in [2, 3, 4]: 
                if not ((self.partner_id or vals.get('partner_id')) and
                        (self.industry_id or vals.get('industry_id')) and
                        (self.commodity or vals.get('commodity')) and
                        (self.volume or vals.get('volume'))):
                    raise UserError(_("Missing Required Fields for '%s' stage.", new_stage.name))
                
            if current_stage_id == 2 and new_stage_id in [3, 4]:
                if not ((self.partner_id or vals.get('partner_id')) and 
                        (self.industry_id or vals.get('industry_id')) and 
                        (self.commodity or vals.get('commodity')) and 
                        (self.volume or vals.get('volume'))):
                    raise UserError(_("Missing Required Fields for '%s' stage.", new_stage.name))
                
            if current_stage_id in [1, 2, 3] and new_stage_id == 4:
                if not (self.payment_term_id or vals.get('payment_term_id')):
                    raise UserError(_("Missing Required Fields for '%s' stage.", new_stage.name))
                if not self.date_deadline:
                    self.date_deadline = fields.Date.today()

            if new_stage.sequence == 1:
                vals['date_seq2'] = now
            elif new_stage.sequence == 2:
                vals['date_seq3'] = now
            elif new_stage.sequence == 3:
                vals['date_seq4'] = now
                vals['date_deadline'] = self.date_deadline or fields.Date.today()
            else:
                vals['date_seq1'] = now
                    
            for lead in self:
                lead._check_expected_revenue(vals)

        return super(CrmLead, self).write(vals)
    
    @api.depends('category_id')
    def _compute_name(self):
        for lead in self:
            if lead.category_id and lead.category_id.name:
                lead.name = lead.category_id.name
    
    #override from odoo_core
    @api.depends('so_ids.state', 'so_ids.currency_id', 'so_ids.amount_untaxed', 'so_ids.date_order', 'so_ids.company_id')
    def _compute_sale_data(self):
        for lead in self:            
            company_currency = lead.company_currency or self.env.company.currency_id
            sale_orders = lead.so_ids.filtered_domain(self._get_lead_sale_order_domain())
            lead.sale_amount_total = sum(
                order.currency_id._convert(
                    order.amount_untaxed, company_currency, order.company_id, order.date_order or fields.Date.today()
                )
                for order in sale_orders
            )
            lead.quotation_count = len(lead.so_ids)
            lead.sale_order_count = len(sale_orders)
    
    #generate crm_ref code
    @api.model_create_multi
    def create(self, vals):              
        for val in vals:
            sequence = self.env['ir.sequence'].next_by_code('crm.ref.sequence')
            val['crm_ref'] = "{}".format(str(sequence))
            if 'stage_id' in val and 'expected_revenue' in val:
                stage_id = val['stage_id']
                expected_revenue = val['expected_revenue']
                stage = self.env['crm.stage'].browse(stage_id)
                if stage.sequence == 2 and expected_revenue == 0:
                    raise UserError("You need to fill in the Expected Revenue for this stage.")
        return super(CrmLead, self).create(vals)
    
    def _prepare_quotation_vals(self, partner_id, lead):
        vals = {'partner_id': partner_id,
                'crm_ref': lead.crm_ref,
                'commodity': lead.commodity,
                'opportunity_ids' : lead.ids,
                'payment_term_id': lead.payment_term_id.id,}
        return vals
    
    #inheirt view sale quotation
    def action_view_sale_quotation(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        action['context'] = {'default_opportunity_id': self.id, 
                            'default_opportunity_ids': self.ids}
        action['domain'] = [('opportunity_ids', 'in', self.id),]
        quotations = self.mapped('so_ids')
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action
    
    #inheirt view sale order
    def action_view_sale_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['context'] = {'default_opportunity_id': self.id,
                            'default_opportunity_ids': self.ids}
        action['domain'] = [('opportunity_ids', 'in', self.id), ('state', 'not in', ['draft', 'sent', 'cancel'])]
        orders = self.mapped('so_ids').filtered(lambda l: l.state not in ('draft', 'sent', 'cancel'))
        if len(orders) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = orders.id
        return action
    
    def _create_order_quotation(self, wiz_partner):
        crm_dict = {'partner_ids': [], 'so_ids': []}
        for rec in self: 
            partner = rec.partner_id.id if rec.partner_id else wiz_partner
            if list(crm_dict.values())[0] and partner in list(crm_dict.values())[0]: 
                quotation = self.env['sale.order'].search([('partner_id', '=', partner),('id', 'in', list(crm_dict.values())[1])])
                quotation.crm_ref = "{}, {}".format(quotation.crm_ref,str(rec.crm_ref))
                quotation.commodity = "{}, {}".format(quotation.commodity,str(rec.commodity)) if rec.commodity else quotation.commodity
                rec.write({'so_ids' : [(4, quotation.id, None)]})
                
            else:         
                vals = self._prepare_quotation_vals(partner, rec)
                order = self.env['sale.order'].create(vals)
                rec.write({'so_ids' : [(4, order.id, None)]})
                for keys,values in crm_dict.items():
                    if keys == 'partner_ids':
                        crm_dict[keys].append(partner)
                    if keys == 'so_ids':
                        crm_dict[keys].append(order.id)        
                        
    def action_new_quotation(self):
        action = super().action_new_quotation()
        action['context']['default_crm_ref'] = self.crm_ref
        action['context']['default_commodity'] = self.commodity
        action['context']['default_payment_term_id'] = self.payment_term_id.id
        action['context']['default_opportunity_ids'] = self.ids
        self.so_ids = self.order_ids.ids
        return action         
    
    def action_create_quotation(self):
       if not all([rec.partner_id.id for rec in self]):            
            return {
            'name': "Select Partner",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',            
            'res_model': 'wizard.select.partner',  
            'views': [(False, 'form')],
            'view_id' : 'view_form_select_partner_wizard',       
            'target': 'new',
            'context' : {'default_crm_ids': self.ids}
            }
       else:
           self._create_order_quotation(wiz_partner=False)
                      
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        active_company = self.env.company
        if view_type == 'form':
            for node in arch.xpath("//field[@name='reason_seq1']"):
                node.set('string', "{} {}".format(active_company.crm_stage_reason_seq1, "Reason"))
            for node in arch.xpath("//field[@name='reason_seq2']"):
                node.set('string', "{} {}".format(active_company.crm_stage_reason_seq2, "Reason"))
            for node in arch.xpath("//field[@name='reason_seq3']"):
                node.set('string', "{} {}".format(active_company.crm_stage_reason_seq3, "Reason"))
            for node in arch.xpath("//field[@name='reason_seq4']"):
                node.set('string', "{} {}".format(active_company.crm_stage_reason_seq4, "Reason"))
            for node in arch.xpath("//field[@name='date_seq1']"):
                node.set('string', "{} {}".format(active_company.crm_stage_reason_seq1, "Date"))
            for node in arch.xpath("//field[@name='date_seq2']"):
                node.set('string', "{} {}".format(active_company.crm_stage_reason_seq2, "Date"))
            for node in arch.xpath("//field[@name='date_seq3']"):
                node.set('string', "{} {}".format(active_company.crm_stage_reason_seq3, "Date"))
            for node in arch.xpath("//field[@name='date_seq4']"):
                node.set('string', "{} {}".format(active_company.crm_stage_reason_seq4, "Date"))
        return arch, view
            
    @api.model
    def action_cron_followup_activity(self):
        activity_type_todo = self.env.ref('mail.mail_activity_data_todo')
        if not activity_type_todo.is_follow_up_activity:
            return
        crm_lead_model_id = self.env['ir.model']._get_id('crm.lead')
        # Execute the query to fetch overdue leads
        self.env.cr.execute("""
            SELECT cl.id, cl.user_id, cl.date_seq1, cl.date_seq2, cl.date_seq3, cs.due_date, cs.sequence
            FROM crm_lead cl JOIN crm_stage cs ON cs.id = cl.stage_id
            WHERE cl.active = TRUE AND cs.due_date > 0
            AND cl.follow_up_state != 'ongoing'
            AND (
                (cs.sequence = 0 AND cl.date_seq1 IS NOT NULL 
                AND cl.date_seq1 + (cs.due_date || ' days')::interval < CURRENT_DATE)
                OR
                (cs.sequence = 1 AND cl.date_seq2 IS NOT NULL 
                AND cl.date_seq2 + (cs.due_date || ' days')::interval < CURRENT_DATE)
                OR
                (cs.sequence = 0 AND cl.date_seq3 IS NOT NULL 
                AND cl.date_seq3 + (cs.due_date || ' days')::interval < CURRENT_DATE)
            )
            ORDER BY cs.sequence
        """)
        results = self.env.cr.fetchall()
        user_ids = {row[1] for row in results if row[1]}  # unique user_ids from results
        users = self.env['res.users'].browse(list(user_ids))
        # Map user_id to user record
        users_map = {user.id: user for user in users}
        activities_to_create = []
        for lead_id, user_id, date_seq1, date_seq2, date_seq3, due_days, sequence in results:
            user = users_map.get(user_id)
            manager_user = None
            if user and user.employee_id and user.employee_id.parent_id:
                manager_user = user.employee_id.parent_id.user_id        
            if sequence == 0:
                date_base = date_seq1
            elif sequence == 1:
                date_base = date_seq2
            else:
                date_base = date_seq3            
            deadline_date = date_base + timedelta(days=due_days)            
            user_ids_to_schedule = [user.id if user else self.env.uid]
            if manager_user:
                user_ids_to_schedule.append(manager_user.id)            
            activities_to_create.extend({
                'res_model_id': crm_lead_model_id,
                'res_id': lead_id,
                'activity_type_id': activity_type_todo.id,
                'user_id': uid,
                'summary': activity_type_todo.follow_up_message,
                'date_deadline': deadline_date,
            } for uid in user_ids_to_schedule)

        if activities_to_create:
            #Extract all lead IDs
            lead_ids = list({act['res_id'] for act in activities_to_create})
            # Update follow_up_state
            crm = self.env['crm.lead'].browse(lead_ids)
            for rec in crm:
                rec.sudo().write({'follow_up_state': 'ongoing'})
            self.env['mail.activity'].create(activities_to_create)

    def action_set_lost(self, **additional_values):
        res = super().action_set_lost(**additional_values)
        if self.probability == 0 and self.active == False:
            self.lost_date = fields.Date.today()
        return res
                