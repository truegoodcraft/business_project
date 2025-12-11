// SPDX-License-Identifier: AGPL-3.0-or-later
import { apiDelete, apiGet, apiPost, apiPut } from '../api.js';

export const RecipesAPI = {
  async list() {
    return apiGet('/app/recipes');
  },
  async get(id) {
    return apiGet(`/app/recipes/${encodeURIComponent(id)}`);
  },
  async create(payload) {
    // { name: string, output_item_id?: number }
    return apiPost('/app/recipes', payload);
  },
  async update(id, payload) {
    // Full document
    return apiPut(`/app/recipes/${encodeURIComponent(id)}`, payload);
  },
  async delete(id) {
    return apiDelete(`/app/recipes/${encodeURIComponent(id)}`);
  },
  async run(payload) {
    // { recipe_id?, output_item_id?, output_qty, components? }
    const normalized = {};

    const recipeId = payload?.recipe_id ?? payload?.recipeId;
    const outputItemId = payload?.output_item_id ?? payload?.outputItemId;
    const outputQty = payload?.output_qty ?? payload?.outputQty;

    const parsedRecipeId = Math.trunc(Number(recipeId));
    if (Number.isInteger(parsedRecipeId) && parsedRecipeId > 0) {
      normalized.recipe_id = parsedRecipeId;
    }

    const parsedOutputItemId = Math.trunc(Number(outputItemId));
    if (Number.isInteger(parsedOutputItemId) && parsedOutputItemId > 0) {
      normalized.output_item_id = parsedOutputItemId;
    }

    const parsedOutputQty = Math.trunc(Number(outputQty));
    if (Number.isInteger(parsedOutputQty) && parsedOutputQty > 0) {
      normalized.output_qty = parsedOutputQty;
    }

    if (Array.isArray(payload?.components)) {
      const components = payload.components
        .map((c) => ({
          item_id: Math.trunc(Number(c.item_id ?? c.itemId)),
          qty: Math.trunc(Number(c.qty)),
        }))
        .filter((c) => Number.isInteger(c.item_id) && c.item_id > 0 && Number.isInteger(c.qty) && c.qty > 0);
      if (components.length > 0) {
        normalized.components = components;
      }
    }

    if (payload?.note) {
      normalized.note = String(payload.note);
    }

    return apiPost('/app/manufacturing/run', normalized);
  },
};
