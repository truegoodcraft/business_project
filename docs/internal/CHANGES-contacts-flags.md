# Contacts Flags Migration (is_vendor, is_org)

## Renames/Removals in UI
- Removed UI control: Role chips ("Vendor | Contact | Both") in Contacts modal.
- Removed UI control: Kind toggle ("Person | Organization") in Contacts modal.
- Added toggles:
  - "Company / Organization" -> form.is_org (boolean)
  - "Treat as Vendor" -> form.is_vendor (boolean)
- List column "Role" now shows a "Vendor" pill when is_vendor=true; otherwise "Contact" label.
- List column "Kind" removed; optional "Organization" pill rendered when is_org=true.

## API Changes (backward-compatible)
- New fields: is_vendor:boolean, is_org:boolean in VendorCreate/Update/Out.
- role is retained for compatibility, derived automatically from is_vendor.
- Filters: is_vendor, is_org added; role filter remains.

## Inventory
- Vendor dropdown now queries /app/vendors?is_vendor=true.
- Typeahead "Create new Vendor" opens Contacts modal with is_vendor pre-toggled.
