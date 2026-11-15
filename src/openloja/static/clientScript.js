// Script para a página de cliente

document.addEventListener('DOMContentLoaded', function() {
  const searchInput = document.getElementById('pedidos-search');
  const table = document.getElementById('pedidos-table');

  if (searchInput && table) {
    searchInput.addEventListener('input', function() {
      filterTable(this.value.toLowerCase());
    });
  }
});

function filterTable(searchTerm) {
  const table = document.getElementById('pedidos-table');
  if (!table) return;

  const rows = table.querySelectorAll('tbody tr');

  rows.forEach(row => {
    const productCell = row.querySelector('td:nth-child(2)');
    if (!productCell) return;

    const productText = productCell.textContent.toLowerCase();
    const statusCell = row.querySelector('td:nth-child(4)');
    const statusText = statusCell ? statusCell.textContent.toLowerCase() : '';

    if (
      productText.includes(searchTerm) ||
      statusText.includes(searchTerm)
    ) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

function logout(event) {
  event.preventDefault();
  fetch('/logout', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .then(response => {
    if (response.ok) {
      window.location.href = '/';
    } else {
      console.error('Erro ao fazer logout');
    }
  })
  .catch(error => console.error('Erro:', error));
}

