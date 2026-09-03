from odoo import models, fields, _
from odoo.tools.misc import format_date
from itertools import groupby
import markupsafe


class AccountReport(models.Model):
    _inherit = 'account.report'

    custom_report_type = fields.Selection([
        ('pl', 'Profit & Loss'),
        ('bs', 'Balance Sheet'),
        ('none', 'Standard Header'),
    ], string="Custom Report Type", default="none", help="PDF/Excel Header Type")

    def _get_custom_report_header_values(self, options):
        """ Returns the values used to render the KMTL custom statement header
        (PDF and Excel exports), or None if this report uses the standard
        Odoo header (see custom_report_type). """
        self.ensure_one()
        if self.custom_report_type not in ('pl', 'bs'):
            return None

        date_to = options.get('date', {}).get('date_to')
        date_str = format_date(self.env, date_to, date_format='dd MMMM y')

        if self.custom_report_type == 'bs':
            statement_title = _("Statements of Financial Position")
            date_line = _("As at %s", date_str)
            unit_label = _("Unit : MMK")
        else:
            statement_title = _("Statement of Income")
            date_line = _("For the month end %s", date_str)
            unit_label = _("Unit : MMK")

        return {
            'company_name': self.env.company.name,
            # 'report_name': self.name,
            'statement_title': statement_title,
            'date_line': date_line,
            'unit_label': unit_label,
        }

    def get_report_information(self, options):
        report_information = super().get_report_information(options)
        if self.custom_report_type in ('pl', 'bs'):
            report_information = dict(report_information)
            custom_display = dict(report_information.get('custom_display', {}))
            pdf_export = dict(custom_display.get('pdf_export', {}))
            pdf_export.setdefault('pdf_export_main', 'kmtl_account_report.pdf_export_main_kmtl')
            custom_display['pdf_export'] = pdf_export
            report_information['custom_display'] = custom_display
        return report_information

    def _get_html_data_for_pdf_export(self, options):
        """Use footer layout without company name for KMTL P&amp;L / Balance Sheet."""
        if self.custom_report_type not in ('pl', 'bs'):
            yield from super()._get_html_data_for_pdf_export(options)
            return

        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or \
            self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        print_options = self.get_options(previous_options={**options, 'export_mode': 'print'})
        if print_options['sections']:
            reports_to_print = self.env['account.report'].browse(
                [section['id'] for section in print_options['sections']]
            )
        else:
            reports_to_print = self

        reports_options = []
        for report in reports_to_print:
            reports_options.append(
                report.get_options(previous_options={**print_options, 'selected_section_id': report.id})
            )

        grouped_reports_by_format = groupby(
            zip(reports_to_print, reports_options),
            key=lambda report: len(report[1]['columns']) > 5
        )

        footer = self.env['ir.actions.report']._render_template(
            'kmtl_account_report.internal_layout_kmtl', values=rcontext
        )
        footer = self.env['ir.actions.report']._render_template(
            'web.minimal_layout',
            values=dict(rcontext, subst=True, body=markupsafe.Markup(footer.decode())),
        )

        for is_landscape, reports_with_options in grouped_reports_by_format:
            bodies = []
            for report, report_options in reports_with_options:
                bodies.append(report._get_pdf_export_html(
                    report_options,
                    report._filter_out_folded_children(report._get_lines(report_options)),
                    additional_context={'base_url': base_url},
                ))
            yield bodies, footer, is_landscape

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        def write_with_colspan(sheet, x, y, value, colspan, style):
            if colspan == 1:
                sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)

        title_format = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        default_format_props = {'font_name': 'Arial', 'font_color': '#666666', 'font_size': 12, 'num_format': '#,##0.00'}
        text_format_props = {'font_name': 'Arial', 'font_color': '#666666', 'font_size': 12}
        date_format_props = {'font_name': 'Arial', 'font_color': '#666666', 'font_size': 12, 'num_format': 'yyyy-mm-dd'}
        workbook_formats = {
            0: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
            },
            1: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'default_indent': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
                'date_indent': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
            },
            2: {
                'default': workbook.add_format({**default_format_props, 'bold': True}),
                'text': workbook.add_format({**text_format_props, 'bold': True}),
                'date': workbook.add_format({**date_format_props, 'bold': True}),
                'initial': workbook.add_format(default_format_props),
                'total': workbook.add_format({**default_format_props, 'bold': True}),
                'default_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'bold': True, 'indent': 2}),
                'initial_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 1}),
            },
            'default': {
                'default': workbook.add_format(default_format_props),
                'text': workbook.add_format(text_format_props),
                'date': workbook.add_format(date_format_props),
                'total': workbook.add_format(default_format_props),
                'default_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'indent': 2}),
            },
        }

        def get_format(content_type='default', level='default'):
            if isinstance(level, int) and level not in workbook_formats:
                workbook_formats[level] = {
                    **workbook_formats['default'],
                    'default_indent': workbook.add_format({**default_format_props, 'indent': level}),
                    'date_indent': workbook.add_format({**date_format_props, 'indent': level}),
                    'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': level - 1}),
                }

            level_formats = workbook_formats[level]
            if '_indent' in content_type and not level_formats.get(content_type):
                return level_formats.get('default_indent', level_formats.get(content_type.removesuffix('_indent'), level_formats['default']))
            return level_formats.get(content_type, level_formats['default'])

        print_mode_self = self.with_context(no_format=True)
        lines = self._filter_out_folded_children(print_mode_self._get_lines(options))

        # For reports with lines generated for accounts, the account name and codes are shown in a single column.
        # To help user post-process the report if they need, we should in such a case split the account name and code in two columns.
        account_lines_split_names = {}
        for line in lines:
            line_model = self._get_model_info_from_id(line['id'])[0]
            if line_model == 'account.account':
                # Reuse the _split_code_name to split the name and code in two values.
                account_lines_split_names[line['id']] = self.env['account.account']._split_code_name(line['name'])

        # Set the (Account) Name column width to 50.
        # If we have account lines and split the name and code in two columns, we will also set the code column.
        if len(account_lines_split_names) > 0:
            sheet.set_column(0, 0, 11)
            sheet.set_column(1, 1, 50)
        else:
            sheet.set_column(0, 0, 50)

        original_x_offset = 1 if len(account_lines_split_names) > 0 else 0

        y_offset = 0
        x_offset = original_x_offset + 1

        # KMTL: left-aligned statement header (company name / statement title / date line / unit)
        kmtl_header = self._get_custom_report_header_values(options)
        if kmtl_header:
            kmtl_header_format = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 15})
            kmtl_report_name_format = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 15, 'align': 'center'})
            kmtl_unit_format = workbook.add_format({'font_name': 'Arial', 'font_size': 10})
            # Center the report name across the full report width, similar to the PDF output.
            data_columns_count = sum(column.get('colspan', 1) for column in options['columns'])
            if options.get('show_growth_comparison'):
                data_columns_count += 1
            report_header_end_col = original_x_offset + 1 + data_columns_count - 1
            # if kmtl_header.get('report_name'):
            #     sheet.merge_range(y_offset, 0, y_offset, report_header_end_col, kmtl_header['report_name'], kmtl_report_name_format)
            #     y_offset += 1
            sheet.write(y_offset, 0, kmtl_header['company_name'], kmtl_header_format)
            y_offset += 1
            
            if kmtl_header['statement_title']:
                sheet.write(y_offset, 0, kmtl_header['statement_title'], kmtl_header_format)
                y_offset += 1
            sheet.write(y_offset, 0, kmtl_header['date_line'], kmtl_header_format)
            y_offset += 1
            if kmtl_header['unit_label']:
                sheet.write(y_offset, 0, kmtl_header['unit_label'], kmtl_header_format)
                y_offset += 1
            y_offset += 1  # blank row before the column headers

        # Add headers.
        # For this, iterate in the same way as done in main_table_header template
        column_headers_render_data = self._get_column_headers_render_data(options)
        for header_level_index, header_level in enumerate(options['column_headers']):
            for header_to_render in header_level * column_headers_render_data['level_repetitions'][header_level_index]:
                colspan = header_to_render.get('colspan', column_headers_render_data['level_colspan'][header_level_index])
                write_with_colspan(sheet, x_offset, y_offset, header_to_render.get('name', ''), colspan, title_format)
                x_offset += colspan
            if options['show_growth_comparison']:
                write_with_colspan(sheet, x_offset, y_offset, '%', 1, title_format)
            y_offset += 1
            x_offset = original_x_offset + 1

        for subheader in column_headers_render_data['custom_subheaders']:
            colspan = subheader.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, subheader.get('name', ''), colspan, title_format)
            x_offset += colspan
        y_offset += 1
        x_offset = original_x_offset + 1

        if account_lines_split_names:
            # If we have a separate account code column, add a title for it
            sheet.write(y_offset, x_offset - 2, _("Code"), title_format)
            sheet.write(y_offset, x_offset - 1, _("Account Name"), title_format)
        sheet.set_column(x_offset, x_offset + len(options['columns']), 10)

        for column in options['columns']:
            colspan = column.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, column.get('name', ''), colspan, title_format)
            x_offset += colspan
        y_offset += 1

        if options.get('order_column'):
            lines = self.sort_lines(lines, options)

        # Disable bold styling for the max level.
        max_level = max(line.get('level', -1) for line in lines) if lines else -1
        if max_level in {0, 1, 2}:
            # Total lines are supposed to be a level above, so we don't touch them.
            for wb_format in (s for s in workbook_formats[max_level] if 'total' not in s):
                workbook_formats[max_level][wb_format].set_bold(False)

        # Add lines.
        for y, line in enumerate(lines):
            level = line.get('level')
            if level == 0:
                y_offset += 1
            elif not level:
                level = 'default'

            line_id = self._parse_line_id(line.get('id'))
            is_initial_line = line_id[-1][0] == 'initial' if line_id else False
            is_total_line = line_id[-1][0] == 'total' if line_id else False

            # Write the first column(s), with a specific style to manage the indentation.
            cell_type, cell_value = self._get_cell_type_value(line)
            account_code_cell_format = get_format('text', level)

            if cell_type == 'date':
                cell_format = get_format('date_indent', level)
            elif is_initial_line:
                cell_format = get_format('initial_indent', level)
            elif is_total_line:
                cell_format = get_format('total_indent', level)
            else:
                cell_format = get_format('default_indent', level)

            x_offset = original_x_offset + 1
            if lines[y]['id'] in account_lines_split_names:
                # Write the Account Code and Name columns.
                code, name = account_lines_split_names[lines[y]['id']]
                # Don't indent the account code and don't format is as a monetary value either.
                sheet.write(y + y_offset, 0, code, account_code_cell_format)
                sheet.write(y + y_offset, 1, name, cell_format)
            else:
                write_method = sheet.write_datetime if cell_type == 'date' else sheet.write
                write_method(y + y_offset, original_x_offset, cell_value, cell_format)

                if 'parent_id' in line and line['parent_id'] in account_lines_split_names:
                    sheet.write(y + y_offset, 1 + original_x_offset, account_lines_split_names[line['parent_id']][0], account_code_cell_format)
                elif account_lines_split_names:
                    sheet.write(y + y_offset, 1 + original_x_offset, "", account_code_cell_format)

            # Write all the remaining cells.
            columns = line['columns']
            if options['show_growth_comparison'] and 'growth_comparison_data' in line:
                columns += [line['growth_comparison_data']]
            for x, column in enumerate(columns, start=x_offset):
                cell_type, cell_value = self._get_cell_type_value(column)

                if cell_type == 'date':
                    cell_format = get_format('date', level)
                elif is_initial_line:
                    cell_format = get_format('initial', level)
                elif is_total_line:
                    cell_format = get_format('total', level)
                else:
                    cell_format = get_format('default', level)

                write_method = sheet.write_datetime if cell_type == 'date' else sheet.write
                write_method(y + y_offset, x + line.get('colspan', 1) - 1, cell_value, cell_format)


class AccountReportCustomHandlerKmtlHeader(models.AbstractModel):
    _name = 'kmtl.account.report.header.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'KMTL Custom Statement Header Handler'

    def _get_custom_display_config(self):
        return {
            'pdf_export': {
                'pdf_export_main': 'kmtl_account_report.pdf_export_main_kmtl',
            },
        }
