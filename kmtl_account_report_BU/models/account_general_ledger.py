from odoo import models, _ , fields

from collections import defaultdict

class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    # same method as _get_query_sums
    # update only query: 'select' and 'group by'
    def _get_query_sums_business_name(self, report, options):
        """ Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :return:                    (query, params)
        """
        options_by_column_group = report._split_options_per_column_group(options)

        params = []
        queries = []

        # Create the currency table.
        # As the currency table is the same whatever the comparisons, create it only once.
        ct_query = report._get_query_currency_table(options)

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================
        for column_group_key, options_group in options_by_column_group.items():
            if not options.get('general_ledger_strict_range'):
                options_group = self._get_options_sum_balance(options_group)

            # Sum is computed including the initial balance of the accounts configured to do so, unless a special option key is used
            # (this is required for trial balance, which is based on general ledger)
            sum_date_scope = 'strict_range' if options_group.get('general_ledger_strict_range') else 'normal'

            query_domain = []

            if options.get('export_mode') == 'print' and options.get('filter_search_bar'):
                query_domain.append(('account_id', 'ilike', options['filter_search_bar']))

            if options_group.get('include_current_year_in_unaff_earnings'):
                query_domain += [('account_id.include_initial_balance', '=', True)]

            tables, where_clause, where_params = report._query_get(options_group, sum_date_scope, domain=query_domain)
            params.append(column_group_key)
            params += where_params
            queries.append(f"""
                SELECT
                    MIN(account_move_line.account_id)                       AS groupby,
                    MIN(account_move_line.id)                               AS line_id,
                    'sum'                                                   AS key,
                    MAX(account_move_line.date)                             AS max_date,
                    %s                                                      AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance,
                    account_move_line.business_name                         AS business_name
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.business_name 
            """)

            # ============================================
            # 2) Get sums for the unaffected earnings.
            # ============================================
            if not options_group.get('general_ledger_strict_range'):
                unaff_earnings_domain = [('account_id.include_initial_balance', '=', False)]

                # The period domain is expressed as:
                # [
                #   ('date' <= fiscalyear['date_from'] - 1),
                #   ('account_id.include_initial_balance', '=', False),
                # ]

                new_options = self._get_options_unaffected_earnings(options_group)
                tables, where_clause, where_params = report._query_get(new_options, 'strict_range', domain=unaff_earnings_domain)
                params.append(column_group_key)
                params += where_params
                queries.append(f"""
                    SELECT
                        MIN(account_move_line.company_id)                       AS company_id,
                        MIN(account_move_line.id)                               AS line_id,
                        'unaffected_earnings'                                   AS key,
                        NULL                                                    AS max_date,
                        %s                                                      AS column_group_key,
                        COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                        SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                        SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance,
                        account_move_line.business_name                         AS business_name
                    FROM {tables}
                    LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                    WHERE {where_clause}
                    GROUP BY account_move_line.business_name 
                """)
        
        union_all_query = ' UNION ALL '.join(queries)
        final_query = f"""
            SELECT * FROM (
                {union_all_query}
            ) AS full_results
            ORDER BY business_name
        """
        return final_query, params


        # return ' UNION ALL '.join(queries), params

    def _query_values_business_name(self, report, options):
        """ Executes the queries, and performs all the computations.

        :return:    [(record, values_by_column_group), ...],  where
                    - record is an account.account record.
                    - values_by_column_group is a dict in the form {column_group_key: values, ...}
                        - column_group_key is a string identifying a column group, as in options['column_groups']
                        - values is a list of dictionaries, one per period containing:
                            - sum:                              {'debit': float, 'credit': float, 'balance': float}
                            - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                            - (optional) unaffected_earnings:   {'debit': float, 'credit': float, 'balance': float}
        """
        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums_business_name(report, options)

        if not query:
            return []

        groupby_business_name = {}
        groupby_companies = {}

        self._cr.execute(query, params)
        for res in self._cr.dictfetchall():
            # No result to aggregate.
            if res['groupby'] is None:
                continue

            column_group_key = res['column_group_key']
            key = res['key']

            business = res['business_name'] or 'Unknown Business'
            if key == 'sum':
                groupby_business_name.setdefault(business, {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_business_name[business][column_group_key][key] = res


            elif key == 'initial_balance':
                groupby_business_name.setdefault(business, {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_business_name[business][column_group_key][key] = res

            elif key == 'unaffected_earnings':
                groupby_companies.setdefault(business, {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_companies[business][column_group_key] = res

        #---------------------------------------------------------------
        # We don't need this path since we are showing by business_name 
        #---------------------------------------------------------------
        # Affect the unaffected earnings to the first fetched account of type 'account.data_unaffected_earnings'.
        # There is an unaffected earnings for each company but it's less costly to fetch all candidate accounts in
        # a single search and then iterate it.
        # if groupby_companies:
        #     equity_unaffected_account_ids_by_company = self.env['account.account'].browse(
        #         self.env['account.account']._name_search(options.get('filter_search_bar'), [
        #             *self.env['account.account']._check_company_domain(list(groupby_companies.keys())),
        #             ('account_type', '=', 'equity_unaffected'),
        #         ])
        #     ).grouped('company_id')

        #     for company_id, groupby_company in groupby_companies.items():
        #         if equity_unaffected_account := equity_unaffected_account_ids_by_company.get(self.env['res.company'].browse(company_id).root_id):
        #             for column_group_key in options['column_groups']:
        #                 groupby_accounts.setdefault(equity_unaffected_account.id, {col_group_key: {'unaffected_earnings': {}} for col_group_key in options['column_groups']})

        #                 if unaffected_earnings := groupby_company.get(column_group_key):
        #                     if groupby_accounts[equity_unaffected_account.id][column_group_key].get('unaffected_earnings'):
        #                         for key in ['amount_currency', 'debit', 'credit', 'balance']:
        #                             groupby_accounts[equity_unaffected_account.id][column_group_key]['unaffected_earnings'][key] += unaffected_earnings[key]
        #                     else:
        #                         groupby_accounts[equity_unaffected_account.id][column_group_key]['unaffected_earnings'] = unaffected_earnings

        # Retrieve the accounts to browse.
        # groupby_accounts.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        # - the unaffected earnings allocation.
        # Note a search is done instead of a browse to preserve the table ordering.

        # get account_id and line_id from result value
        def extract_sum_data(column_group_results):
            for result in column_group_results.values():
                if isinstance(result, dict):
                    sum_data = result.get('sum')
                    if sum_data and isinstance(sum_data, dict):
                        return {
                            'account_id': sum_data.get('groupby'),
                            'line_id': sum_data.get('line_id'),
                        }
            return {
                'account_id': None,
                'line_id': None,
            }
    
        return [
            (business, column_group_results, extract_sum_data(column_group_results))
            for business, column_group_results in groupby_business_name.items()
        ]

    def _dynamic_lines_generator_business_name(self, report, options, all_column_groups_expression_totals, warnings=None):
        lines = []
        date_from = fields.Date.from_string(options['date']['date_from'])
        company_currency = self.env.company.currency_id

        totals_by_column_group = defaultdict(lambda: {'debit': 0, 'credit': 0, 'balance': 0})

        account_ids = set()
        line_ids = set()

        query_results = list(self._query_values_business_name(report, options))

        for _, _, meta in query_results:
            account_ids.add(meta['account_id'])
            line_ids.add(meta['line_id'])
        
        account_map = {a.id: a for a in self.env['account.account'].browse(account_ids)}
        move_line_map = {ml.id: ml for ml in self.env['account.move.line'].browse(line_ids)}

        for business_name, column_group_results, meta in query_results:
            eval_dict = {}
            has_lines = False

            # add custom code------------------------
            account_id = meta['account_id']
            line_id = meta['line_id']
            #----------------------------------------

            for column_group_key, results in column_group_results.items():
                account_sum = results.get('sum', {})
                account_un_earn = results.get('unaffected_earnings', {})

                account_debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
                account_credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
                account_balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

                eval_dict[column_group_key] = {
                    'amount_currency': account_sum.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0),
                    'debit': account_debit,
                    'credit': account_credit,
                    'balance': account_balance,
                }

                max_date = account_sum.get('max_date')
                has_lines = has_lines or (max_date and max_date >= date_from)

                totals_by_column_group[column_group_key]['debit'] += account_debit
                totals_by_column_group[column_group_key]['credit'] += account_credit
                totals_by_column_group[column_group_key]['balance'] += account_balance

            # add custom code
            account = account_map.get(account_id)
            move_line = move_line_map.get(line_id)
            lines.append(self._get_account_title_line_trial_balance(report, options, business_name, account,line_id,move_line, has_lines, eval_dict))

        # Report total line.
        for totals in totals_by_column_group.values():
            totals['balance'] = company_currency.round(totals['balance'])

        # Tax Declaration lines.
        journal_options = report._get_options_journals(options)
        if len(options['column_groups']) == 1 and len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
            lines += self._tax_declaration_lines(report, options, journal_options[0]['type'])

        # Total line
        lines.append(self._get_total_line(report, options, totals_by_column_group))

        return [(0, line) for line in lines]
    
    def _get_account_title_line_trial_balance(self, report, options, business_name, account, line_id, move_line, has_lines, eval_dict):
        line_columns = []
        value_map = {
                'account_code': account.code,
                'account_name': account.name,
                'plan_2': move_line.plan_2,
                'plan_3': move_line.plan_3,
                'plan_4': move_line.plan_4,
                'plan_5': move_line.plan_5,
            }
        
        for column in options['columns']:
            col_value = eval_dict[column['column_group_key']].get(column['expression_label'])
            col_expr_label = column['expression_label']

            value = None if col_value is None or (col_expr_label == 'amount_currency' and not account.currency_id) else col_value

            value = value_map.get(col_expr_label) if value_map.get(col_expr_label) else value

            line_columns.append(report._build_column_dict(
                value,
                column,
                options=options,
                currency=account.currency_id if col_expr_label == 'amount_currency' else None,
            ))

        line_id = report._get_generic_line_id('account.move.line', line_id)
        is_in_unfolded_lines = any(
            report._get_res_id_from_line_id(line_id, 'account.account') == account.id
            for line_id in options.get('unfolded_lines')
        )
        return {
            'id': line_id,
            'name': f'{business_name}',
            'columns': line_columns,
            'level': 1,
            'unfoldable': has_lines,
            'unfolded': has_lines and (is_in_unfolded_lines or options.get('unfold_all')),
            'expand_function': '_report_expand_unfoldable_line_general_ledger',
        }

