# Inventory Guide

## Items and Types

An item is anything BUS Core tracks in stock. A material is an input you buy or consume. A component is an input that may itself have been made or assembled. A product is an item you manufacture or sell; mark it with **This is a product** and set a usual sale price when appropriate.

These labels help operators organize work. The selected dimension and unit control which quantities the backend accepts.

## Units

Choose the real measurement dimension and a matching unit when creating an item. Do not use `ea` for something you actually consume by mass or volume. Recipe lines, stock movement, and manufacturing quantities must use units valid for the item's dimension.

Changing how an established item is measured can make history confusing. Test your unit choices with one small receipt and recipe first.

## Batches and FIFO

Stock-in and purchasing create batches with quantities and unit costs. **FIFO** means first in, first out: when stock is consumed, BUS Core allocates the oldest available batch first. The item detail view shows batch quantities and costs.

FIFO affects COGS. If you buy the same material at different prices, the oldest available cost is consumed first.

## Stock In

Use stock-in for purchases, opening quantities, or other inventory entering the shop. Enter a unit cost when you need the batch to carry cost into manufacturing and Finance.

## Stock Out

Stock Out removes inventory FIFO. Choose the honest reason: **Sold**, **Loss**, **Theft**, or **Other**. Sold can record a sale cash event and price for count items. If the available quantity is too low, the operation fails with a shortage instead of silently overselling.

## Adjustments

An adjustment changes quantity by a positive or negative amount. Use it for a counted correction, not as a substitute for normal purchasing, manufacturing, or sales. Record enough context to explain the correction later.

## Vendors

Vendors/contacts identify who supplies an item. Assigning one makes the catalog easier to understand, but does not create inventory or a purchase automatically.

## Common Mistakes

- Creating a recipe before creating its output product.
- Treating the product's sale price as its inventory cost.
- Omitting material unit cost, then expecting meaningful COGS.
- Mixing count, mass, or volume units for the same item.
- Using an adjustment when a stock-in, stock-out, or manufacturing run is the real event.
- Entering the full catalog before testing one end-to-end workflow.

Next: [Recipes Guide](Recipes-Guide.md).
