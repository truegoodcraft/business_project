# Getting Started

BUS Core is local-first shop infrastructure for inventory, recipes, manufacturing, and cost visibility. It is not a hosted SaaS account and it is not a full POS or accounting package.

Core is feature-frozen and stability-focused after v1.3.2. It remains maintained, open-source, local-first infrastructure; future Core updates focus on safety, reliability, tester blockers, data protection, release hygiene, small UX clarification, and documentation. New major workflow or domain expansion moves to BUS Pro discovery.

## Choose Your Install Path

- [Windows Install](Windows-Install.md) for a local Windows setup.
- [Docker Install](Docker-Install.md) for a container-based setup.
- [Synology NAS Docker Setup (Beta)](Synology-NAS-Docker-Setup-Beta.md) if you are specifically testing on Synology NAS.

## First Launch

On first launch, choose the path that matches what you are doing:

- Use demo mode to explore seeded sample data.
- Use Start Fresh when you are ready to create or reset the real-shop database.
- Export a backup first from Settings -> Administration -> Backup Export if you need to keep existing real-shop data.

Demo data is separate from the real-shop database.

## First Workflow

Run this path once before entering a large catalog:

1. Add a vendor from Inventory or while creating an item.
2. Add a raw material with an opening batch and unit cost.
3. Add a product, check "This is a product", and enter its usual sale price.
4. Open Recipes and create a recipe.
5. Select the product as the Output Product.
6. Add the raw material or component rows the recipe consumes.
7. Open Manufacturing and select the recipe.
8. Try a shortage case first if you want to verify the warning path.
9. Run a successful manufacturing pass and confirm stock changes.
10. Stock out the product as sold.
11. Confirm the sale price starts from the usual product price and warns if you enter less.
12. Open Finance and review sales, COGS, gross profit, and date presets.
13. Check Settings -> Administration -> Backup Export, update status, Help, support, and report-issue links.

## Key Words

- Product: the inventory item you build or sell.
- Recipe: the list of materials or components needed to make a product.
- Output Product: the product a recipe adds to stock when manufactured.
- Stock Out: reducing inventory for a sale, loss, theft, or correction.

## Still Not Included

BUS Core still does not include full POS, full accounting, QuickBooks/Wave sync, automatic reorder, full job scheduling, cloud accounts, cloud sync, telemetry, payment links, customer portals, or recurring billing.

## If You Are Beta Testing

- Read the [Beta Testing Guide](Beta-Testing-Guide.md).
- Report problems in [Bug Reports](Bug-Reports.md).
- Suggest workflow improvements in [Feature Requests](Feature-Requests.md).

## Scope Note

Keep setup small at first. Add one vendor, one material, one product, one recipe, one manufacturing run, and one sale before expanding the catalog.
