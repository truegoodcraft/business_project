// SPDX-License-Identifier: AGPL-3.0-or-later
import { apiGet, apiPost } from '../api.js';

export const RecipesAPI = {
  async list() {
    return apiGet('/app/recipes');
  },
  async get(id) {
    return apiGet(`/app/recipes/${encodeURIComponent(id)}`);
  },
  async run(payload) {
    // { recipe_id, multiplier }
    return apiPost('/app/manufacturing/run', payload);
  },
};
