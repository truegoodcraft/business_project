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
    return apiPost('/app/manufacturing/run', payload);
  },
};
