# Recipes Guide

## Product, Recipe, and Output Product

- **Product:** the inventory item you make or sell.
- **Recipe:** the definition of inputs consumed to make an output.
- **Output Product:** the existing product item that receives stock after a successful manufacturing run.

Create the product first. A recipe cannot point to an output item that does not exist.

## What a Recipe Contains

A recipe has a name, an output product, an output quantity and unit, and one or more input item lines with quantities and units. When you manufacture a multiple of that recipe, BUS Core scales the required inputs and output.

Example: product `Finished serving board`; recipe `Serving board - standard`; output `1 ea`; input `1 ea hardwood blank`.

## Cost Behavior

The recipe does not set the product's sale price. During manufacturing, FIFO input batch costs are consumed and rolled into the output batch's unit cost. That cost becomes relevant to COGS when the product is later sold.

## Naming Guidance

Name products as things found on a shelf or invoice. Name recipes as build definitions, including size or revision when useful. Avoid giving the product and recipe identical names if operators could confuse them.

## Common Confusion

- A recipe is not stock and cannot be sold.
- An output product is not an extra recipe ingredient.
- Product sale price is revenue guidance, not manufacturing cost.
- A recipe definition does not reserve materials or schedule work.
- Saving a recipe does not move inventory; running manufacturing does.

Next: [Manufacturing Guide](Manufacturing-Guide.md).
