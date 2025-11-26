function toggleThumbnails(button) {
    const container = button.nextElementSibling;
    if (container.style.display === 'none') {
        container.style.display = 'block';
        button.textContent = '-';
    } else {
        container.style.display = 'none';
        button.textContent = '+';
    }
}
