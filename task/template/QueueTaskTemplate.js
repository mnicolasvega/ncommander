function toggleQueueTaskContent(button) {
    const table = button.closest('table');
    const progressRow = table.querySelector('.row-progress');
    const contentRow = table.querySelector('.row-content');
    
    if (contentRow.style.display === 'none') {
        if (progressRow) progressRow.style.display = 'table-row';
        contentRow.style.display = 'table-row';
        button.textContent = '−';
    } else {
        if (progressRow) progressRow.style.display = 'none';
        contentRow.style.display = 'none';
        button.textContent = '+';
    }
}
