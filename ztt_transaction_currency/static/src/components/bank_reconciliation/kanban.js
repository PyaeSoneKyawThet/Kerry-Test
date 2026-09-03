/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban"; 

patch(BankRecKanbanController.prototype, {
    getOne2ManyColumns() {
        const columns = super.getOne2ManyColumns(...arguments);
        const lineIdsRecords = this.state.bankRecRecordData.line_ids.records;

        columns.push(
            ["currency_rate", _t("Currency Rate")],
        );

        return columns;
    },

    formatNumber(value, digits = 4) {
        if (typeof value === 'number') {
            return value.toFixed(digits);
        }
        return value;
    }
    
});
