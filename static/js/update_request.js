document.addEventListener('DOMContentLoaded', () => {
    const requestSelect = document.getElementById('request-select');
    const selectedRequestDetailsDiv = document.getElementById('selected-request-details');
    const updateFormSection = document.getElementById('update-form-section');
    const updateRequestForm = document.getElementById('update-request-form');
    const currentRequestIdInput = document.getElementById('current-request-id');

    const messageBox = document.getElementById('message-box');
    const errorBox = document.getElementById('error-box');

    const bulkUpdateExcelForm = document.getElementById('bulk-update-excel-form');
    const bulkUpdateExcelFileInput = document.getElementById('bulk-update-excel-file-input');
    const bulkUploadMessageBox = document.getElementById('bulk-upload-message');
    const bulkUploadErrorBox = document.getElementById('bulk-upload-error');

    const downloadUpdateDataBtn = document.getElementById('download-update-data-btn');
    const downloadUpdateTemplateBtn = document.getElementById('download-update-template-btn');


    const displayElements = {
        'request-no': document.getElementById('display-request-no'),
        'requested-by': document.getElementById('display-requested-by'),
        'department': document.getElementById('display-department'),
        'category': document.getElementById('display-category'),
        'request-date': document.getElementById('display-request-date'),
        'request-title': document.getElementById('display-request-title'),
        'description': document.getElementById('display-description'),
        'current-status': document.getElementById('display-current-status'), // New element
    };

    const updateFormInputs = {
        'srs_sent_date': document.getElementById('srs-sent-date'),
        'srs_approval_date': document.getElementById('srs-approval-date'),
        'estimation_received_date': document.getElementById('estimation-received-date'),
        'indent_sent_date': document.getElementById('indent-sent-date'),
        'signed_indent_received_date': document.getElementById('signed-indent-received-date'),
        'estimated_man_hours_ba': document.getElementById('estimated-man-hours-ba'),
        'estimated_man_hours_dev': document.getElementById('estimated-man-hours-dev'),
        'estimated_man_hours_tester': document.getElementById('estimated-man-hours-tester'),
        'development_start_date': document.getElementById('development-start-date'),
        'uat_mail_date': document.getElementById('uat-mail-date'),
        'uat_confirmation_date': document.getElementById('uat-confirmation-date'),
        'current_status': document.getElementById('current-status'), // New element
    };

    function showMessage(element, message, type = 'success') {
        element.textContent = message;
        element.classList.remove('hidden', 'success', 'error');
        element.classList.add(type === 'success' ? 'success' : 'error');
        setTimeout(() => {
            element.classList.add('hidden');
        }, 5000);
    }

    async function fetchRequestsForSelection() {
        try {
            const response = await fetch('/api/requests');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const requests = await response.json();
            
            requestSelect.innerHTML = '<option value="">-- Select Request No, Title --</option>';
            requests.forEach(req => {
                const option = document.createElement('option');
                option.value = req.id;
                option.textContent = `${req.request_no} - ${req.request_title} (Req by: ${req.requested_by})`;
                requestSelect.appendChild(option);
            });

        } catch (error) {
            console.error('Error fetching requests for selection:', error);
            showMessage(errorBox, 'Failed to load requests for selection. ' + error.message, 'error');
        }
    }

    async function fetchRequestDetails(requestId) {
        if (!requestId) {
            selectedRequestDetailsDiv.classList.add('hidden');
            updateFormSection.classList.add('hidden');
            updateRequestForm.reset();
            currentRequestIdInput.value = '';
            return;
        }

        try {
            const response = await fetch(`/api/request-details/${requestId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const details = await response.json();
            
            for (const key in displayElements) {
                displayElements[key].textContent = details[key] || 'N/A';
            }
            selectedRequestDetailsDiv.classList.remove('hidden');

            currentRequestIdInput.value = details.id;
            for (const key in updateFormInputs) {
                if (updateFormInputs[key].type === 'date' && details[key]) {
                    updateFormInputs[key].value = details[key].split('T')[0];
                } else if (updateFormInputs[key].type === 'number' && details[key] === null) {
                    updateFormInputs[key].value = '';
                }
                else {
                    updateFormInputs[key].value = details[key] || '';
                }
            }
            updateFormSection.classList.remove('hidden');

        } catch (error) {
            console.error('Error fetching request details:', error);
            showMessage(errorBox, 'Failed to load request details. ' + error.message, 'error');
            selectedRequestDetailsDiv.classList.add('hidden');
            updateFormSection.classList.add('hidden');
        }
    }

    requestSelect.addEventListener('change', (e) => {
        fetchRequestDetails(e.target.value);
    });

    updateRequestForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const requestId = currentRequestIdInput.value;
        if (!requestId) {
            showMessage(errorBox, 'Please select a request to update.', 'error');
            return;
        }

        const updateData = {};
        for (const key in updateFormInputs) {
            const value = updateFormInputs[key].value;
            if (value !== null && value !== '') {
                updateData[key] = updateFormInputs[key].type === 'number' ? parseInt(value, 10) : value;
            } else {
                updateData[key] = null;
            }
        }
        
        delete updateData.id;

        try {
            const response = await fetch(`/api/update-request/${requestId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updateData)
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(messageBox, result.message, 'success');
                fetchRequestDetails(requestId); 
            } else {
                showMessage(errorBox, result.error || 'An error occurred.', 'error');
            }
        } catch (error) {
            console.error('Error updating request details:', error);
            showMessage(errorBox, 'An unexpected error occurred. ' + error.message, 'error');
        }
    });

    bulkUpdateExcelForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const file = bulkUpdateExcelFileInput.files[0];
        if (!file) {
            showMessage(bulkUploadErrorBox, 'Please select an Excel file for bulk update.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/update-request/bulk-upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(bulkUploadMessageBox, result.message, 'success');
                if (currentRequestIdInput.value) {
                    fetchRequestDetails(currentRequestIdInput.value);
                }
                bulkUpdateExcelFileInput.value = '';
                if (result.failed_rows && result.failed_rows.length > 0) {
                    showMessage(bulkUploadErrorBox, 'Some rows failed to upload: ' + result.failed_rows.join('; '), 'error');
                }
            } else {
                showMessage(bulkUploadErrorBox, result.error || 'An error occurred during bulk upload.', 'error');
            }
        } catch (error) {
            console.error('Error uploading bulk update Excel file:', error);
            showMessage(bulkUploadErrorBox, 'An unexpected error occurred during bulk upload. ' + error.message, 'error');
        }
    });

    downloadUpdateDataBtn.addEventListener('click', () => {
        window.location.href = '/api/update-request/download';
    });

    downloadUpdateTemplateBtn.addEventListener('click', () => {
        window.location.href = '/api/update-request/template';
    });

    fetchRequestsForSelection();
});