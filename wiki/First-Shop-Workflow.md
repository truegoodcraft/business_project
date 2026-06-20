# First Shop Workflow

Use one simple example to learn the whole path. This example makes one finished product from one stocked material.

## 1. Add a Vendor

Open **Inventory**, then create a vendor/contact while adding an item or through the available vendor controls. Use the supplier you buy the material from. Vendors provide purchasing context; they are not stock themselves.

## 2. Add a Raw Material

Select **+ Add Item**. Name the material clearly, choose its dimension and unit, assign the vendor if useful, and save it. Stock the material in with a quantity and unit cost. That receipt creates a costed batch.

Example: `Hardwood blank`, count unit `ea`, 10 on hand at $4.00 each.

## 3. Add the Product

Add another inventory item for what you sell. Check **This is a product** and enter its usual sale price.

Example: `Finished serving board`, count unit `ea`, usual price $35.00.

The product must exist before its recipe because the recipe needs an Output Product to point to.

## 4. Create a Recipe

Open **Recipes** and create a recipe such as `Serving board - standard`. Select the finished product as **Output Product**, set the output quantity and unit, and add the material rows the run consumes.

Keep product and recipe names distinct. The product is stocked and sold; the recipe is the instruction for making it.

## 5. Manufacture

Open **Manufacturing**, choose the recipe and run quantity, then submit the run. BUS Core consumes the required material batches FIFO and adds a costed batch of the output product. History identifies runs as `Run #N`.

To learn the safety behavior, you can first request more than is available. A shortage names the item and shows need, have, and missing quantities. The failed run does not partially consume inputs or create output. Reduce the run or stock in more material, then try again.

## 6. Stock Out a Sale

Open **Inventory > Stock Out**, select the product, choose reason **Sold**, enter the quantity, and confirm the sale price. For count items, BUS Core starts with the product's usual price when one is set. A lower price produces a warning but can still be used.

Reasons such as loss, theft, or other reduce inventory without representing a normal sale. Sold is currently supported for count items.

## 7. Review Finance

Open **Finance** and choose a date preset such as **Last 30 days**. Review Gross Sales, Net Sales, COGS, Gross Profit, Expenses, and Net Profit. The sale price supplies revenue; FIFO input cost flows through manufacturing into the product cost and then COGS when sold.

Finance is operational visibility, not a replacement for bookkeeping, tax filing, or professional accounting advice. See [Finance Guide](Finance-Guide.md).

## 8. Back Up

Open **Settings > Administration > Backup Export**, create an encrypted export, and confirm it appears under available exports.

Next: [Inventory Guide](Inventory-Guide.md) and [Backup and Restore](Backups-and-Data-Persistence.md).
