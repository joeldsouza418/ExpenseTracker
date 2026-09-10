/**
 * Expense Tracker - Interactive UI Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const typeIncomeBtn = document.getElementById('typeIncomeBtn');
  const typeExpenseBtn = document.getElementById('typeExpenseBtn');
  const typeHiddenInput = document.getElementById('typeInput');
  const categoryInput = document.getElementById('categoryInput');
  const categoryPillsContainer = document.getElementById('categoryPills');
  const dateInput = document.getElementById('dateInput');
  const transactionForm = document.getElementById('transactionForm');

  // Category presets
  const categories = {
    Income: [
      'Salary',
      'Freelance',
      'Investments',
      'Bonus',
      'Rental Income',
      'Gifts',
      'Other Income'
    ],
    Expense: [
      'Food & Dining',
      'Groceries',
      'Rent / Housing',
      'Utilities',
      'Transportation',
      'Shopping',
      'Entertainment',
      'Health & Medical',
      'Education',
      'Travel',
      'Other Expense'
    ]
  };

  // Set default date to today if empty
  if (dateInput && !dateInput.value) {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    dateInput.value = `${yyyy}-${mm}-${dd}`;
  }

  // Render Category Presets
  function renderCategoryPills(type) {
    if (!categoryPillsContainer) return;
    categoryPillsContainer.innerHTML = '';

    const list = categories[type] || [];
    list.forEach(cat => {
      const pill = document.createElement('span');
      pill.className = 'cat-pill';
      pill.textContent = cat;

      if (categoryInput && categoryInput.value.trim().toLowerCase() === cat.toLowerCase()) {
        pill.classList.add('selected');
      }

      pill.addEventListener('click', () => {
        if (categoryInput) {
          categoryInput.value = cat;
          // Update visual pill selection
          document.querySelectorAll('.cat-pill').forEach(p => p.classList.remove('selected'));
          pill.classList.add('selected');
          categoryInput.focus();
        }
      });

      categoryPillsContainer.appendChild(pill);
    });
  }

  // Switch Transaction Type
  function setTransactionType(type) {
    if (typeHiddenInput) typeHiddenInput.value = type;

    if (type === 'Income') {
      typeIncomeBtn?.classList.add('active');
      typeExpenseBtn?.classList.remove('active');
    } else {
      typeExpenseBtn?.classList.add('active');
      typeIncomeBtn?.classList.remove('active');
    }

    renderCategoryPills(type);
  }

  typeIncomeBtn?.addEventListener('click', () => setTransactionType('Income'));
  typeExpenseBtn?.addEventListener('click', () => setTransactionType('Expense'));

  // Initialize with currently selected type (defaults to Expense or Income)
  const initialType = typeHiddenInput ? typeHiddenInput.value || 'Expense' : 'Expense';
  setTransactionType(initialType);

  // Sync category input typing with pill highlights
  categoryInput?.addEventListener('input', () => {
    const val = categoryInput.value.trim().toLowerCase();
    document.querySelectorAll('.cat-pill').forEach(pill => {
      if (pill.textContent.trim().toLowerCase() === val) {
        pill.classList.add('selected');
      } else {
        pill.classList.remove('selected');
      }
    });
  });

  // Client-side validation enhancement
  if (transactionForm) {
    transactionForm.addEventListener('submit', (e) => {
      const amountInput = document.getElementById('amountInput');
      let valid = true;

      if (!typeHiddenInput.value) {
        valid = false;
      }

      if (!categoryInput.value.trim()) {
        categoryInput.classList.add('is-invalid');
        valid = false;
      } else {
        categoryInput.classList.remove('is-invalid');
      }

      const amountVal = parseFloat(amountInput.value);
      if (isNaN(amountVal) || amountVal <= 0) {
        amountInput.classList.add('is-invalid');
        valid = false;
      } else {
        amountInput.classList.remove('is-invalid');
      }

      if (!dateInput.value) {
        dateInput.classList.add('is-invalid');
        valid = false;
      } else {
        dateInput.classList.remove('is-invalid');
      }

      if (!valid) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  }

  // Delete modal setup
  const deleteModal = document.getElementById('deleteConfirmModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', (event) => {
      const button = event.relatedTarget;
      const txId = button.getAttribute('data-tx-id');
      const txDesc = button.getAttribute('data-tx-desc');
      const form = document.getElementById('deleteForm');
      const descEl = document.getElementById('deleteModalDesc');

      if (form) form.action = `/delete/${txId}`;
      if (descEl) descEl.textContent = txDesc || 'this transaction';
    });
  }
});
