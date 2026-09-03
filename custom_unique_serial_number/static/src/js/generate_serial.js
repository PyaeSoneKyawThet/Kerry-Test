/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import {
    GenerateDialog, GenerateSerials, ImportLots
} from "@stock/widgets/generate_serial";
import { Component, useRef, onMounted } from "@odoo/owl";

patch(GenerateDialog.prototype, {
    setup () {
        super.setup(...arguments);

        const get_serial_value = async() => {
            const picking_id = this.props.move.data.picking_id[0];
            let picking_info = await this.orm.searchRead("stock.picking",[["id", "=", picking_id]], ["staff_location_id"]);

            /* Get document location code */
            const staff_location_id = picking_info[0].staff_location_id[0];
            let document_location_info = await this.orm.searchRead("staff.location",[["id", "=", staff_location_id]], ["code"]);
            const document_location_code = document_location_info[0].code;

            /* Get document location line(fixed_asset') code */
            let document_location_line_info = await this.orm.searchRead("document.location.line",[["staff_location_id", "=", staff_location_id],["operation_type", "=", 'fixed_asset']], ["staff_location_prefix"]);
            const staff_location_prefix = document_location_line_info[0].staff_location_prefix;

            /* Get product's item_code and serial_number */
            const product_id = this.props.move.data.product_id[0];
            let product_info = await this.orm.searchRead("product.product",[["id", "=", product_id]], ["next_serial_number","item_code"]);
            const product_code = product_info[0].item_code;
            let serial_number = product_info[0].next_serial_number;
            const serial_number_prefix = serial_number.toString().padStart(5, '0');

            let unique_serial_no = `${staff_location_prefix}-${document_location_code}-${product_code}-${serial_number_prefix}`;

            return unique_serial_no;
        }

        onMounted(async() => {
            if (this.props.type === 'serial') {
                const unique_serial_no = await get_serial_value();
                this.nextSerial.el.value = unique_serial_no;
            }
        });
    },
    
    
});



