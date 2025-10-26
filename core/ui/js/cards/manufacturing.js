(function(){
  if (!window.API || !window.Dom || !window.Modals) {
    console.error('Card missing API helpers: manufacturing');
    return;
  }

  const { el, bindDisabledWithProGate } = window.Dom;
  const API = window.API;

  function asArray(value){
    return Array.isArray(value) ? value : [];
  }

  function parseJson(text){
    if (!text || !text.trim()) return {};
    try {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed;
      }
    } catch (error) {
      throw new Error('Invalid JSON: ' + error.message);
    }
    throw new Error('Provide a JSON object.');
  }

  async function render(container){
    if (!el || !API) {
      container.textContent = 'UI helpers unavailable.';
      return;
    }

    const state = {
      items: [],
      recipes: [],
      selectedItemId: null,
      recipeStatus: el('div', { class: 'status-box' }, 'Select a product to manage recipes.'),
      batchStatus: el('div', { class: 'status-box' }, 'Ready to execute batch runs.'),
    };

    const title = el('h2', {}, 'Manufacturing');

    const productSelect = el('select');
    const recipeList = el('div', { class: 'recipe-list', style: { display: 'grid', gap: '12px' } });
    const recipeEditor = el('textarea', { placeholder: 'Recipe JSON or notes' });
    const saveRecipe = el('button', { type: 'button' }, 'Save Recipe');
    const refreshRecipesBtn = el('button', { type: 'button', class: 'secondary' }, 'Refresh Recipes');

    const recipeSection = el('section', {}, [
      el('div', { class: 'section-title' }, 'Item Recipes'),
      el('div', { class: 'form-grid' }, [
        el('label', {}, ['Product', productSelect]),
        el('label', {}, ['New Recipe', recipeEditor]),
      ]),
      el('div', { class: 'actions' }, [saveRecipe, refreshRecipesBtn]),
      recipeList,
      state.recipeStatus,
    ]);

    const inputsArea = el('textarea', { placeholder: 'Inputs JSON e.g. {"1": 2}' });
    const outputsArea = el('textarea', { placeholder: 'Outputs JSON e.g. {"5": 1}' });
    const noteInput = el('input', { placeholder: 'Optional note' });
    const runButton = el('button', { type: 'button' }, 'Run Batch');
    bindDisabledWithProGate(runButton, 'batch_run');

    const batchSection = el('section', {}, [
      el('div', { class: 'section-title' }, 'Batch Run'),
      el('div', { class: 'form-grid' }, [
        el('label', {}, ['Inputs', inputsArea]),
        el('label', {}, ['Outputs', outputsArea]),
        el('label', {}, ['Note', noteInput]),
      ]),
      runButton,
      state.batchStatus,
    ]);

    const rfqContainer = el('div', { class: 'status-box' }, 'RFQ module loading…');
    const rfqSection = el('section', {}, [
      el('div', { class: 'section-title' }, 'Request for Quote'),
      el('div', { class: 'badge-note' }, 'Generate vendor-ready RFQs (Pro feature).'),
      rfqContainer,
    ]);

    container.replaceChildren(title, recipeSection, batchSection, rfqSection);

    function renderRecipeRows(){
      recipeList.innerHTML = '';
      if (!state.recipes.length) {
        recipeList.appendChild(el('div', { class: 'badge-note' }, 'No recipes stored for this item.'));
        return;
      }
      state.recipes.forEach(recipe => {
        const preview = el('pre', { class: 'status-box' }, recipe.label || '(empty)' );
        const remove = el('button', { type: 'button', class: 'danger' }, 'Delete');
        remove.addEventListener('click', () => {
          if (!window.Modals) return;
          window.Modals.confirm('Delete Recipe', 'Delete this recipe entry?', async () => {
            try {
              await API.delete(`/attachments/${recipe.id}`);
              await loadRecipes();
            } catch (error) {
              state.recipeStatus.textContent = 'Delete failed: ' + (error && error.message ? error.message : String(error));
            }
          });
        });
        const entry = el('div', { class: 'card' }, [
          el('div', { class: 'section-title' }, `Recipe #${recipe.id}`),
          preview,
          el('div', { class: 'badge-note' }, `Reader: ${recipe.reader_id}`),
          el('div', { class: 'actions' }, [remove]),
        ]);
        recipeList.appendChild(entry);
      });
    }

    function populateProducts(){
      const items = asArray(state.items);
      productSelect.innerHTML = '';
      if (!items.length) {
        productSelect.appendChild(el('option', { value: '' }, 'No items available'));
        state.selectedItemId = null;
        renderRecipeRows();
        return;
      }
      items.forEach(item => {
        const option = el('option', { value: String(item.id) }, `${item.name || 'Item'} (#${item.id})`);
        productSelect.appendChild(option);
      });
      const match = items.find(item => item.id === state.selectedItemId) || items[0];
      state.selectedItemId = match ? match.id : null;
      productSelect.value = state.selectedItemId ? String(state.selectedItemId) : '';
    }

    async function loadItems(){
      try {
        const items = await API.get('/items');
        state.items = asArray(items);
        populateProducts();
        if (state.selectedItemId) {
          await loadRecipes();
        } else {
          state.recipeStatus.textContent = 'Create an item to define recipes.';
        }
      } catch (error) {
        state.recipeStatus.textContent = 'Failed to load items: ' + (error && error.message ? error.message : String(error));
      }
    }

    async function loadRecipes(){
      if (!state.selectedItemId) return;
      try {
        state.recipeStatus.textContent = 'Loading recipes…';
        const attachments = await API.get(`/attachments/item/${state.selectedItemId}`);
        state.recipes = asArray(attachments).filter(entry => entry.reader_id === 'recipe');
        renderRecipeRows();
        state.recipeStatus.textContent = `Loaded ${state.recipes.length} recipe(s).`;
      } catch (error) {
        state.recipeStatus.textContent = 'Failed to load recipes: ' + (error && error.message ? error.message : String(error));
      }
    }

    productSelect.addEventListener('change', async () => {
      const value = productSelect.value;
      state.selectedItemId = value ? Number(value) : null;
      await loadRecipes();
    });

    refreshRecipesBtn.addEventListener('click', () => {
      if (!state.selectedItemId) {
        state.recipeStatus.textContent = 'Select an item first.';
        return;
      }
      loadRecipes();
    });

    saveRecipe.addEventListener('click', async () => {
      if (!state.selectedItemId) {
        state.recipeStatus.textContent = 'Select an item first.';
        return;
      }
      const content = recipeEditor.value.trim();
      if (!content) {
        state.recipeStatus.textContent = 'Enter recipe details before saving.';
        return;
      }
      try {
        // Validate JSON if provided but keep raw text
        try {
          parseJson(content);
        } catch (_error) {
          // allow non-JSON recipes; ignore validation error
        }
        await API.post(`/attachments/item/${state.selectedItemId}`, {
          reader_id: 'recipe',
          label: content,
        });
        recipeEditor.value = '';
        state.recipeStatus.textContent = 'Recipe saved.';
        await loadRecipes();
      } catch (error) {
        state.recipeStatus.textContent = 'Save failed: ' + (error && error.message ? error.message : String(error));
      }
    });

    runButton.addEventListener('click', async () => {
      state.batchStatus.textContent = 'Running batch…';
      try {
        const inputs = parseJson(inputsArea.value);
        const outputs = parseJson(outputsArea.value);
        const note = noteInput.value.trim() || null;
        const result = await API.post('/inventory/run', { inputs, outputs, note });
        if (result && result.locked) return;
        state.batchStatus.textContent = 'Batch completed.';
        document.dispatchEvent(new CustomEvent('items:refresh'));
      } catch (error) {
        state.batchStatus.textContent = 'Batch failed: ' + (error && error.message ? error.message : String(error));
      }
    });

    if (window.Cards && window.Cards.rfq && typeof window.Cards.rfq.render === 'function') {
      window.Cards.rfq.render(rfqContainer);
    } else {
      rfqContainer.textContent = 'RFQ module unavailable.';
    }

    await loadItems();
  }

  function init() {}

  if (window.Cards && typeof window.Cards.register === 'function') {
    window.Cards.register('manufacturing', { init, render });
  }
})();
