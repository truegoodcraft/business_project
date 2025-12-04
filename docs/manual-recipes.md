# Recipes Page Manual Verification

Use this checklist to validate the standalone `#/recipes` experience and its integration with Manufacturing.

1. Navigate to `#/recipes`.
   - Confirm the left list renders with a filter box and "+ New" button.
   - Right side shows the editor shell prompting to select a recipe.
2. Create a recipe from the list panel.
   - Set the recipe name, then choose a single **Output Item**.
   - Add multiple **input** lines with positive `qty_stored` values.
3. Edit the recipe.
   - Change the recipe name and verify the list refreshes.
   - Update a line’s qty or role, then remove a line and confirm the table refreshes.
4. Navigate to `#/manufacturing`.
   - Ensure the new recipe appears in the dropdown and projections use `qty_stored` values.
   - Use the “Manage Recipes” link to return to `#/recipes`.
5. Confirm all interactions go through `/app/*` APIs with no ad-hoc local files.
