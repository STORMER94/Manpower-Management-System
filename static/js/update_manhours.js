document.addEventListener('DOMContentLoaded', () => {
    const manhoursExcelUploadForm = document.getElementById('manhours-excel-upload-form');
    const manhoursExcelFileInput = document.getElementById('manhours-excel-file-input');
    const manhoursExcelMessageBox = document.getElementById('manhours-excel-message');
    const manhoursExcelErrorBox = document.getElementById('manhours-excel-error');
    const actualManhoursList = document.getElementById('actual-manhours-list');
    const noManhoursMessage = document.getElementById('no-manhours-message');

    const downloadManhoursDataBtn = document.getElementById('download-manhours-data-btn');
    const downloadManhoursTemplateBtn = document.getElementById('download-manhours-template-btn');

    // Function to display messages
    function showMessage(element, message, type = 'success') {
        element.textContent = message;
        element.classList.remove('hidden', 'success', 'error');
        element.classList.add(type === 'success' ? 'success' : 'error');
        setTimeout(() => {
            element.classList.add('hidden');
        }, 5000); // Hide after 5 seconds
    }

    // Function to fetch and display actual man-hours
    async function fetchActualManHours() {
        try {
            const response = await fetch('/api/actual-manhours');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            renderActualManHours(data);
        } catch (error) {
            console.error('Error fetching actual man-hours:', error);
            showMessage(manhoursExcelErrorBox, 'Failed to load actual man-hours. ' + error.message, 'error');
        }
    }

    // Function to render actual man-hours in the table
    function renderActualManHours(data) {
        actualManhoursList.innerHTML = ''; // Clear existing list
        if (data.length === 0) {
            noManhoursMessage.classList.remove('hidden');
        } else {
            noManhoursMessage.classList.add('hidden');
            data.forEach(entry => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="py-3 px-4">${entry.request_no}</td>
                    <td class="py-3 px-4">${entry.task_date || 'N/A'}</td> <!-- Display Task Date -->
                    <td class="py-3 px-4">${entry.stakeholder_name}</td>
                    <td class="py-3 px-4">${entry.actual_man_hours}</td>
                `;
                actualManhoursList.appendChild(row);
            });
        }
    }

    // Handle Excel upload for actual man-hours
    manhoursExcelUploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const file = manhoursExcelFileInput.files[0];
        if (!file) {
            showMessage(manhoursExcelErrorBox, 'Please select an Excel file to upload.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/actual-manhours/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(manhoursExcelMessageBox, result.message, 'success');
                fetchActualManHours(); // Refresh list after upload
                manhoursExcelFileInput.value = ''; // Clear file input
                if (result.failed_rows && result.failed_rows.length > 0) {
                    showMessage(manhoursExcelErrorBox, 'Some rows failed to upload: ' + result.failed_rows.join('; '), 'error');
                }
            } else {
                showMessage(manhoursExcelErrorBox, result.error || 'An error occurred during upload.', 'error');
            }
        } catch (error) {
            console.error('Error uploading Excel file:', error);
            showMessage(manhoursExcelErrorBox, 'An unexpected error occurred during upload. ' + error.message, 'error');
        }
    });

    // Event listener for download all man-hours data button
    downloadManhoursDataBtn.addEventListener('click', () => {
        window.location.href = '/api/actual-manhours/download';
    });

    // Event listener for download man-hours template button
    downloadManhoursTemplateBtn.addEventListener('click', () => {
        window.location.href = '/api/actual-manhours/template';
    });

    // Initial fetch of actual man-hours when the page loads
    fetchActualManHours();
});