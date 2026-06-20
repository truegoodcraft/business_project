# Manufacturing Guide

## How a Run Works

Open **Manufacturing**, select a recipe, enter the run quantity in a valid unit, and submit. BUS Core calculates the scaled inputs, verifies availability, consumes FIFO input batches, and creates an output batch.

Successful history entries use `Run #N`, where `N` is the run identifier.

## Shortages

If an input is short, the message identifies the item and reports the needed, available, and missing quantities. A shortage returns a failed run; it does not partially consume inputs or create output.

To continue, either stock in the missing input, reduce the requested run, or correct the recipe if its requirement is wrong. Do not use a manual adjustment merely to bypass a real shortage.

## FIFO and Output Cost

Inputs are consumed from the oldest available batches first. Their allocated costs are combined into the manufactured output cost. The output is then available as a costed inventory batch for later stock-out and COGS reporting.

## What Manufacturing Does Not Do

Manufacturing does not provide full job scheduling, automatic reorder, purchase ordering, labor planning, machine scheduling, or material reservation. It also does not sell the output automatically; record the later sale with Stock Out.

Next: [Finance Guide](Finance-Guide.md).
