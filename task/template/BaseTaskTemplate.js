function toggleTaskContent(button) {
    const table = button.closest('table');
    const contentRow = table.querySelector('.row-content');
    if (contentRow.style.display === 'none') {
        contentRow.style.display = 'table-row';
        button.textContent = '−';
    } else {
        contentRow.style.display = 'none';
        button.textContent = '+';
    }
}
