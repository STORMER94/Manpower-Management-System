document.addEventListener('DOMContentLoaded', () => {
    const reportTableBody = document.getElementById('report-table-body');
    const noReportDataMessage = document.getElementById('no-report-data-message');
    const messageBox = document.getElementById('message-box');
    const errorBox = document.getElementById('error-box');

    const reportFilterForm = document.getElementById('report-filter-form');
    const filterRequestNoInput = document.getElementById('filter-request-no');
    const filterDepartmentInput = document.getElementById('filter-department');
    const filterCategoryInput = document.getElementById('filter-category');
    const filterRequestDateInput = document.getElementById('filter-request-date');
    const clearFiltersBtn = document.getElementById('clear-filters-btn');
    const downloadFilteredReportBtn = document.getElementById('download-filtered-report-btn');

    const statusDropdownButton = document.getElementById('status-dropdown-button');
    const statusDropdownContent = document.getElementById('status-dropdown-content');
    const statusFilterCheckboxes = document.querySelectorAll('input[name="status-filter"]');
    const selectedStatusCountSpan = document.getElementById('selected-status-count');
    let selectedStatuses = [];

    const manhoursBreakupModal = document.getElementById('manhours-breakup-modal');
    const closeBreakupModalBtn = document.getElementById('close-breakup-modal');
    const breakupRequestNoSpan = document.getElementById('breakup-request-no');
    const breakupTableBody = document.getElementById('breakup-table-body');
    const noBreakupDataMessage = document.getElementById('no-breakup-data-message');


    function showMessage(element, message, type = 'success') {
        element.textContent = message;
        element.classList.remove('hidden', 'success', 'error');
        element.classList.add(type === 'success' ? 'success' : 'error');
        setTimeout(() => {
            element.classList.add('hidden');
        }, 5000);
    }

    async function fetchReport() {
        const queryParams = new URLSearchParams();
        if (filterRequestNoInput.value) queryParams.append('request_no', filterRequestNoInput.value);
        if (filterDepartmentInput.value) queryParams.append('department', filterDepartmentInput.value);
        if (filterCategoryInput.value) queryParams.append('category', filterCategoryInput.value);
        if (filterRequestDateInput.value) queryParams.append('request_date', filterRequestDateInput.value);
        
        selectedStatuses.forEach(status => {
            queryParams.append('current_status', status);
        });

        try {
            const response = await fetch(`/api/report?${queryParams.toString()}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const reportData = await response.json();
            renderReport(reportData);
        } catch (error) {
            console.error('Error fetching report:', error);
            showMessage(errorBox, 'Failed to load report. ' + error.message, 'error');
        }
    }

    function renderReport(data) {
        reportTableBody.innerHTML = '';
        if (data.length === 0) {
            noReportDataMessage.classList.remove('hidden');
        } else {
            noReportDataMessage.classList.add('hidden');
            data.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="py-3 px-4">${row.request_no || 'N/A'}</td>
                    <td class="py-3 px-4">${row.current_status || 'N/A'}</td> <!-- New Column Data -->
                    <td class="py-3 px-4">${row.requested_by || 'N/A'}</td>
                    <td class="py-3 px-4">${row.department || 'N/A'}</td>
                    <td class="py-3 px-4">${row.category || 'N/A'}</td>
                    <td class="py-3 px-4">${row.request_date || 'N/A'}</td>
                    <td class="py-3 px-4">${row.request_title || 'N/A'}</td>
                    <td class="py-3 px-4">${row.srs_sent_date || 'N/A'}</td>
                    <td class="py-3 px-4">${row.srs_approval_date || 'N/A'}</td>
                    <td class="py-3 px-4">${row.estimation_received_date || 'N/A'}</td>
                    <td class="py-3 px-4">${row.indent_sent_date || 'N/A'}</td>
                    <td class="py-3 px-4">${row.signed_indent_received_date || 'N/A'}</td>
                    <td class="py-3 px-4">${row.estimated_man_hours_ba || 'N/A'}</td>
                    <td class="py-3 px-4">
                        <span class="clickable-mh" data-request-id="${row.request_internal_id}" data-request-no="${row.request_no}" data-role="BA">
                            ${row.actual_man_hours_ba || 'N/A'}
                        </span>
                    </td>
                    <td class="py-3 px-4">${row.estimated_man_hours_developers || 'N/A'}</td>
                    <td class="py-3 px-4">
                        <span class="clickable-mh" data-request-id="${row.request_internal_id}" data-request-no="${row.request_no}" data-role="Developer">
                            ${row.actual_man_hours_developers || 'N/A'}
                        </span>
                    </td>
                    <td class="py-3 px-4">${row.estimated_man_hours_tester || 'N/A'}</td>
                    <td class="py-3 px-4">
                        <span class="clickable-mh" data-request-id="${row.request_internal_id}" data-request-no="${row.request_no}" data-role="Tester">
                            ${row.actual_man_hours_tester || 'N/A'}
                        </span>
                    </td>
                    <td class="py-3 px-4">${row.total_estimated !== null ? row.total_estimated : 'N/A'}</td>
                    <td class="py-3 px-4">${row.total_actual !== null ? row.total_actual : 'N/A'}</td>
                    <td class="py-3 px-4">${row.difference_man_hours !== null ? row.difference_man_hours : 'N/A'}</td>
                    <td class="py-3 px-4">${row.development_start_date || 'N/A'}</td>
                    <td class="py-3 px-4">${row.uat_mail_date || 'N/A'}</td>
                    <td class="py-3 px-4">${row.uat_confirmation_date || 'N/A'}</td>
                    <td class="py-3 px-4">${row.tat_days !== null ? row.tat_days.toFixed(0) : 'N/A'}</td>
                `;
                reportTableBody.appendChild(tr);
            });
            addBreakupEventListeners();
        }
    }

    function addBreakupEventListeners() {
        document.querySelectorAll('.clickable-mh').forEach(span => {
            span.addEventListener('click', async (e) => {
                const requestId = e.target.dataset.requestId;
                const requestNo = e.target.dataset.requestNo;
                const role = e.target.dataset.role;
                if (requestId && role) {
                    await fetchManhoursBreakup(requestId, requestNo, role);
                }
            });
        });
    }

    async function fetchManhoursBreakup(requestId, requestNo, role) {
        try {
            const response = await fetch(`/api/report/manhours-breakup/${requestId}?role=${role}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const breakupData = await response.json();
            
            breakupRequestNoSpan.textContent = requestNo + ` (Role: ${role})`;
            breakupTableBody.innerHTML = '';
            if (breakupData.length === 0) {
                noBreakupDataMessage.classList.remove('hidden');
            } else {
                noBreakupDataMessage.classList.add('hidden');
                breakupData.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="py-2 px-3">${item.stakeholder_name || 'N/A'}</td>
                        <td class="py-2 px-3">${item.stakeholder_role || 'N/A'}</td>
                        <td class="py-2 px-3">${item.task_date || 'N/A'}</td>
                        <td class="py-2 px-3">${item.actual_man_hours !== null ? item.actual_man_hours : 'N/A'}</td>
                    `;
                    breakupTableBody.appendChild(tr);
                });
            }
            manhoursBreakupModal.classList.remove('hidden');
        } catch (error) {
            console.error('Error fetching man-hours breakup:', error);
            showMessage(errorBox, 'Failed to load man-hours breakup. ' + error.message, 'error');
        }
    }

    closeBreakupModalBtn.addEventListener('click', () => {
        manhoursBreakupModal.classList.add('hidden');
    });

    reportFilterForm.addEventListener('submit', (e) => {
        e.preventDefault();
        fetchReport();
    });

    statusDropdownButton.addEventListener('click', (event) => {
        event.stopPropagation();
        statusDropdownContent.classList.toggle('hidden');
    });

    statusFilterCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            selectedStatuses = Array.from(statusFilterCheckboxes)
                                .filter(cb => cb.checked)
                                .map(cb => cb.value);
            selectedStatusCountSpan.textContent = `${selectedStatuses.length} selected`;
        });
    });

    document.addEventListener('click', (event) => {
        if (!statusDropdownContent.contains(event.target) && event.target !== statusDropdownButton) {
            statusDropdownContent.classList.add('hidden');
        }
    });


    clearFiltersBtn.addEventListener('click', () => {
        filterRequestNoInput.value = '';
        filterDepartmentInput.value = '';
        filterCategoryInput.value = '';
        filterRequestDateInput.value = '';
        
        statusFilterCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        selectedStatuses = [];
        selectedStatusCountSpan.textContent = '0 selected';

        fetchReport();
    });

    downloadFilteredReportBtn.addEventListener('click', () => {
        const queryParams = new URLSearchParams();
        if (filterRequestNoInput.value) queryParams.append('request_no', filterRequestNoInput.value);
        if (filterDepartmentInput.value) queryParams.append('department', filterDepartmentInput.value);
        if (filterCategoryInput.value) queryParams.append('category', filterCategoryInput.value);
        if (filterRequestDateInput.value) queryParams.append('request_date', filterRequestDateInput.value);
        
        selectedStatuses.forEach(status => {
            queryParams.append('current_status', status);
        });

        window.location.href = `/api/report/download?${queryParams.toString()}`;
    });


    fetchReport();
});