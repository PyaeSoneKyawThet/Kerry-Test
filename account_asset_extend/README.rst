Business Workflow Summary (Project Handover – PSM, 29-04-2026)
    Technical Name: account_asset_extend

1. Purchase & Stock Receipt
=======================================
    | User creates Purchase Order and receives products via Stock Picking.
    | System captures:
    |   - Destination Location
    |   - Staff Location
    |   - Serial/Lot Number

2. Stock Move Line Processing
=======================================
    | Each stock move line stores:
    |   - Product
    |   - Serial Number / Model Serial No
    | When transfer is Done, system allows asset creation.

3. Asset Creation
=======================================
    | User triggers “Create Asset” from stock move line.
    | System automatically creates an asset with:
    |   - Product & Asset Model
    |   - Depreciation settings
    |   - Purchase value
    |   - Location & Staff Location
    |   - Serial / Model Serial No

4. Auto Reference Generation
========================================
    | Asset gets unique reference sequence based on Asset Model.
    | If sequence doesn’t exist → system auto-creates it.

5. Asset Information Enrichment
=========================================
    | User can link:
    |   - Employee → auto-fill Department
    |   - Receipt → auto-fill Locations
    |   - Vendor Bill → auto-fill Bill Date & Vendor

6. Bill Linking
==========================================
    | User links vendor bill to asset.
    | System filters available vendor bills:
    |   - Based on related Purchase Order
    |   - Only valid (non-cancelled) invoices

7. Depreciation Processing
==========================================
    | System generates depreciation entries.
    | Each journal entry includes: Staff Location (passed from asset)
    |   - analytic is applied only to the journal item using the asset’s Expense Account; all other lines do not carry analytic information.

8. Asset Reporting Fields
==========================================
    | System computes:
    |   - Remaining Value
    |   - Accumulated Depreciation
    |   - Year-to-Date Depreciation

9. Asset Disposal
==========================================
    | User can dispose asset → creates disposal record.
    | On disposal:
    |   - Journal entries are created
    |   - Staff Location is propagated to disposal entries

10. Data Consistency Automation
==========================================
    | Serial Number flows from stock → asset
    | Location & staff location remain consistent across:
    |   - Stock
    |   - Asset
    |   - Accounting entries