// SPDX-License-Identifier: AGPL-3.0-or-later
import { apiDelete, apiGet, apiPatch, apiPost } from '../api.js';

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
    // { name?: string, output_item_id?: number }
    return apiPatch(`/app/recipes/${encodeURIComponent(id)}`, payload);
  },
  async addItem(recipeId, payload) {
    // { item_id: number, role: 'input'|'output', qty_stored: number }
    return apiPost(`/app/recipes/${encodeURIComponent(recipeId)}/items`, payload);
  },
  async updateItem(recipeId, itemId, payload) {
    // { role?: 'input'|'output', qty_stored?: number }
    return apiPatch(`/app/recipes/${encodeURIComponent(recipeId)}/items/${encodeURIComponent(itemId)}`, payload);
  },
  async removeItem(recipeId, itemId) {
    return apiDelete(`/app/recipes/${encodeURIComponent(recipeId)}/items/${encodeURIComponent(itemId)}`);
  },
  async run(payload) {
    // { recipe_id, multiplier }
    return apiPost('/app/manufacturing/run', payload);
  },
};
