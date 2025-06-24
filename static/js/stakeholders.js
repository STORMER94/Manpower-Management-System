document.addEventListener('DOMContentLoaded', () => {
    const stakeholderForm = document.getElementById('stakeholder-form');
    const stakeholderIdInput = document.getElementById('stakeholder-id');
    const nameInput = document.getElementById('name');
    const roleSelect = document.getElementById('role');
    const submitButton = stakeholderForm.querySelector('button[type="submit"]');
    const cancelEditButton = document.getElementById('cancel-edit-btn');
    const stakeholdersList = document.getElementById('stakeholders-list');
    const noStakeholdersMessage = document.getElementById('no-stakeholders-message');
    const messageBox = document.getElementById('message-box');
    const errorBox = document.getElementById('error-box');

    // Function to display messages
    function showMessage(element, message, type = 'success') {
        element.textContent = message;
        element.classList.remove('hidden', 'success', 'error');
        element.classList.add(type === 'success' ? 'success' : 'error'); // Apply specific class
        setTimeout(() => {
            element.classList.add('hidden');
        }, 5000); // Hide after 5 seconds
    }

    // Function to fetch and display stakeholders
    async function fetchStakeholders() {
        try {
            const response = await fetch('/api/stakeholders');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const stakeholders = await response.json();
            renderStakeholders(stakeholders);
        } catch (error) {
            console.error('Error fetching stakeholders:', error);
            showMessage(errorBox, 'Failed to load stakeholders. ' + error.message, 'error');
        }
    }

    // Function to render stakeholders in the table
    function renderStakeholders(stakeholders) {
        stakeholdersList.innerHTML = ''; // Clear existing list
        if (stakeholders.length === 0) {
            noStakeholdersMessage.classList.remove('hidden');
        } else {
            noStakeholdersMessage.classList.add('hidden');
            stakeholders.forEach(stakeholder => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="py-3 px-4">${stakeholder.name}</td>
                    <td class="py-3 px-4">${stakeholder.role}</td>
                    <td class="py-3 px-4">
                        <button class="btn btn-edit mr-2" data-id="${stakeholder.id}" data-name="${stakeholder.name}" data-role="${stakeholder.role}">Edit</button>
                        <button class="btn btn-delete" data-id="${stakeholder.id}">Delete</button>
                    </td>
                `;
                stakeholdersList.appendChild(row);
            });
            addEventListenersToButtons();
        }
    }

    // Add event listeners to dynamically created edit/delete buttons
    function addEventListenersToButtons() {
        document.querySelectorAll('.btn-edit').forEach(button => {
            button.onclick = (e) => {
                const id = e.target.dataset.id;
                const name = e.target.dataset.name;
                const role = e.target.dataset.role;
                
                stakeholderIdInput.value = id;
                nameInput.value = name;
                roleSelect.value = role;
                
                submitButton.textContent = 'Update Stakeholder';
                cancelEditButton.classList.remove('hidden');
            };
        });

        document.querySelectorAll('.btn-delete').forEach(button => {
            button.onclick = async (e) => {
                const id = e.target.dataset.id;
                // Custom confirmation dialog instead of alert/confirm
                if (await showConfirmDialog('Are you sure you want to delete this stakeholder? This action cannot be undone.')) {
                    deleteStakeholder(id);
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

    // Handle form submission (add/update)
    stakeholderForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const id = stakeholderIdInput.value;
        const name = nameInput.value;
        const role = roleSelect.value;

        if (!name || !role) {
            showMessage(errorBox, 'Please fill in all fields.', 'error');
            return;
        }

        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/stakeholders/${id}` : '/api/stakeholders';

        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, role })
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(messageBox, result.message, 'success');
                stakeholderForm.reset();
                stakeholderIdInput.value = ''; // Clear ID after successful operation
                submitButton.textContent = 'Add Stakeholder';
                cancelEditButton.classList.add('hidden');
                fetchStakeholders(); // Refresh the list
            } else {
                showMessage(errorBox, result.error || 'An error occurred.', 'error');
            }
        } catch (error) {
            console.error('Error submitting stakeholder:', error);
            showMessage(errorBox, 'An unexpected error occurred. ' + error.message, 'error');
        }
    });

    // Handle delete operation
    async function deleteStakeholder(id) {
        try {
            const response = await fetch(`/api/stakeholders/${id}`, {
                method: 'DELETE'
            });

            const result = await response.json();
            if (response.ok) {
                showMessage(messageBox, result.message, 'success');
                fetchStakeholders(); // Refresh the list
            } else {
                showMessage(errorBox, result.error || 'An error occurred.', 'error');
            }
        } catch (error) {
            console.error('Error deleting stakeholder:', error);
            showMessage(errorBox, 'An unexpected error occurred. ' + error.message, 'error');
        }
    }

    // Cancel edit button functionality
    cancelEditButton.addEventListener('click', () => {
        stakeholderForm.reset();
        stakeholderIdInput.value = '';
        submitButton.textContent = 'Add Stakeholder';
        cancelEditButton.classList.add('hidden');
    });

    // Initial fetch of stakeholders when the page loads
    fetchStakeholders();
});