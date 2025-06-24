document.addEventListener('DOMContentLoaded', () => {
    const requestForm = document.getElementById('request-form');
    const requestIdInput = document.getElementById('request-id');
    const requestNoInput = document.getElementById('request-no');
    const requestedByInput = document.getElementById('requested-by');
    const departmentInput = document.getElementById('department');
    const categoryInput = document.getElementById('category');
    const requestDateInput = document.getElementById('request-date');
    const requestTitleInput = document.getElementById('request-title');
    const descriptionInput = document.getElementById('description');
    const submitButton = requestForm.querySelector('button[type="submit"]');
    const cancelEditButton = document.getElementById('cancel-request-edit-btn');
    const requestsList = document.getElementById('requests-list');
    const noRequestsMessage = document.getElementById('no-requests-message');
    const messageBox = document.getElementById('message-box');
    const errorBox = document.getElementById('error-box');

    const excelUploadForm = document.getElementById('excel-upload-form');
    const excelFileInput = document.getElementById('excel-file-input');
    const excelUploadMessageBox = document.getElementById('excel-upload-message');
    const excelUploadErrorBox = document.getElementById('excel-upload-error');

    const downloadRequestsDataBtn = document.getElementById('download-requests-data-btn');
    const downloadRequestsTemplateBtn = document.getElementById('download-requests-template-btn');


    // Function to display messages
    function showMessage(element, message, type = 'success') {
        element.textContent = message;
        element.classList.remove('hidden', 'success', 'error');
        element.classList.add(type === 'success' ? 'success' : 'error');
        setTimeout(() => {
            element.classList.add('hidden');
        }, 5000); // Hide after 5 seconds
    }

    // Function to fetch and display requests
    async function fetchRequests() {
        try {
            const response = await fetch('/api/requests');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const requests = await response.json();
            renderRequests(requests);
        } catch (error) {
            console.error('Error fetching requests:', error);
            showMessage(errorBox, 'Failed to load requests. ' + error.message, 'error');
        }
    }

    // Function to render requests in the table
    function renderRequests(requests) {
        requestsList.innerHTML = ''; // Clear existing list
        if (requests.length === 0) {
            noRequestsMessage.classList.remove('hidden');
        } else {
            noRequestsMessage.classList.add('hidden');
            requests.forEach(request => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="py-3 px-4">${request.request_no}</td>
                    <td class="py-3 px-4">${request.requested_by}</td>
                    <td class="py-3 px-4">${request.department}</td>
                    <td class="py-3 px-4">${request.category}</td>
                    <td class="py-3 px-4">${request.request_date}</td>
                    <td class="py-3 px-4">${request.request_title}</td>
                    <td class="py-3 px-4">
                        <button class="btn btn-edit mr-2" data-id="${request.id}"
                            data-request-no="${request.request_no}"
                            data-requested-by="${request.requested_by}"
                            data-department="${request.department}"
                            data-category="${request.category}"
                            data-request-date="${request.request_date}"
                            data-request-title="${request.request_title}"
                            data-description="${request.description || ''}">Edit</button>
                        <button class="btn btn-delete" data-id="${request.id}">Delete</button>
                    </td>
                `;
                requestsList.appendChild(row);
            });
            addEventListenersToButtons();
        }
    }

    // Add event listeners to dynamically created edit/delete buttons
    function addEventListenersToButtons() {
        document.querySelectorAll('.btn-edit').forEach(button => {
            button.onclick = (e) => {
                const dataset = e.target.dataset;
                requestIdInput.value = dataset.id;
                requestNoInput.value = dataset.requestNo;
                requestedByInput.value = dataset.requestedBy;
                departmentInput.value = dataset.department;
                categoryInput.value = dataset.category;
                requestDateInput.value = dataset.requestDate;
                requestTitleInput.value = dataset.requestTitle;
                descriptionInput.value = dataset.description;

                submitButton.textContent = 'Update Request';
                cancelEditButton.classList.remove('hidden');
            };
        });

        document.querySelectorAll('.btn-delete').forEach(button => {
            button.onclick = async (e) => {
                const id = e.target.dataset.id;
                // Custom confirmation dialog instead of alert/confirm
                if (await showConfirmDialog('Are you sure you want to delete this request? This action cannot be undone.')) {
                    deleteRequest(id);
                }
            };
        });
    }

    // Custom confirmation dialog
    function showConfirmDialog(message) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50';
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 shadow-lg max-w-sm w-full">
                    <p class="text-lg font-semibold text-gray-800 mb-4">${message}</p>
                    <div class="flex justify-end gap-3">
                        <button id="confirm-no" class="btn btn-secondary">Cancel</button>
                        <button id="confirm-yes" class="btn btn-delete">Delete</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            document.getElementById('confirm-yes').onclick = () => {
                modal.remove();
                resolve(true);
            };
            document.getElementById('confirm-no').onclick = () => {
                modal.remove();
                resolve(false);
            };
        });
    }


    // Handle request form submission (add/update)
    requestForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const id = requestIdInput.value;
        const requestData = {
            request_no: requestNoInput.value,
            requested_by: requestedByInput.value,
            department: departmentInput.value,
            category: categoryInput.value,
            request_date: requestDateInput.value,
            request_title: requestTitleInput.value,
            description: descriptionInput.value
        };

        if (!requestData.request_no || !requestData.requested_by || !requestData.department ||
            !requestData.category || !requestData.request_date || !requestData.request_title) {
            showMessage(errorBox, 'Please fill in all required fields.', 'error');
            return;
        }

        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/requests/${id}` : '/api/requests';

        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(messageBox, result.message, 'success');
                requestForm.reset();
                requestIdInput.value = '';
                submitButton.textContent = 'Add Request';
                cancelEditButton.classList.add('hidden');
                fetchRequests(); // Refresh the list
            } else {
                showMessage(errorBox, result.error || 'An error occurred.', 'error');
            }
        } catch (error) {
            console.error('Error submitting request:', error);
            showMessage(errorBox, 'An unexpected error occurred. ' + error.message, 'error');
        }
    });

    // Handle delete request operation
    async function deleteRequest(id) {
        try {
            const response = await fetch(`/api/requests/${id}`, {
                method: 'DELETE'
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(messageBox, result.message, 'success');
                fetchRequests(); // Refresh the list
            } else {
                showMessage(errorBox, result.error || 'An error occurred.', 'error');
            }
        } catch (error) {
            console.error('Error deleting request:', error);
            showMessage(errorBox, 'An unexpected error occurred. ' + error.message, 'error');
        }
    }

    // Handle Excel upload for requests
    excelUploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const file = excelFileInput.files[0];
        if (!file) {
            showMessage(excelUploadErrorBox, 'Please select an Excel file to upload.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/requests/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(excelUploadMessageBox, result.message, 'success');
                fetchRequests(); // Refresh requests list after upload
                excelFileInput.value = ''; // Clear file input
                if (result.failed_rows && result.failed_rows.length > 0) {
                    showMessage(excelUploadErrorBox, 'Some rows failed to upload: ' + result.failed_rows.join(', '), 'error');
                }
            } else {
                showMessage(excelUploadErrorBox, result.error || 'An error occurred during upload.', 'error');
            }
        } catch (error) {
            console.error('Error uploading Excel file:', error);
            showMessage(excelUploadErrorBox, 'An unexpected error occurred during upload. ' + error.message, 'error');
        }
    });

    // Event listener for download all requests data button
    downloadRequestsDataBtn.addEventListener('click', () => {
        window.location.href = '/api/requests/download';
    });

    // Event listener for download requests template button
    downloadRequestsTemplateBtn.addEventListener('click', () => {
        window.location.href = '/api/requests/template';
    });

    // Cancel request edit button functionality
    cancelEditButton.addEventListener('click', () => {
        requestForm.reset();
        requestIdInput.value = '';
        submitButton.textContent = 'Add Request';
        cancelEditButton.classList.add('hidden');
    });

    // Initial fetch of requests when the page loads
    fetchRequests();
});