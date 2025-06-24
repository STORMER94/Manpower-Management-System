document.addEventListener('DOMContentLoaded', () => {
    const messageBox = document.getElementById('message-box');
    const errorBox = document.getElementById('error-box');

    function showMessage(element, message, type = 'success') {
        element.textContent = message;
        element.classList.remove('hidden', 'success', 'error');
        element.classList.add(type === 'success' ? 'success' : 'error');
        setTimeout(() => {
            element.classList.add('hidden');
        }, 5000);
    }

    async function fetchDashboardData() {
        try {
            const response = await fetch('/api/dashboard/data');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            renderRequestsByCategoryChart(data.requests_by_category);
            renderManHoursComparisonChart(data.man_hours_comparison);

        } catch (error) {
            console.error('Error fetching dashboard data:', error);
            showMessage(errorBox, 'Failed to load dashboard data. ' + error.message, 'error');
        }
    }

    function renderRequestsByCategoryChart(data) {
        const ctx = document.getElementById('requestsByCategoryChart').getContext('2d');
        if (Chart.getChart(ctx)) {
            Chart.getChart(ctx).destroy();
        }

        const labels = data.map(item => item.category);
        const counts = data.map(item => item.count);
        const backgroundColors = [
            '#4299e1', '#667eea', '#805ad5', '#d53f8c', '#ed64a6',
            '#f6ad55', '#ecc94b', '#a0aec0', '#48bb78', '#38b2ac'
        ];

        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: backgroundColors.slice(0, labels.length),
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            font: {
                                family: 'Inter',
                                size: 14
                            },
                            color: '#475569'
                        }
                    },
                    title: {
                        display: false,
                        text: 'Requests by Category'
                    },
                    tooltip: {
                        callbacks: {
                            title: function(tooltipItems) {
                                const item = tooltipItems[0];
                                let label = item.chart.data.labels[item.dataIndex];
                                if (Array.isArray(label)) {
                                  return label.join(' ');
                                } else {
                                  return label;
                                }
                            },
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed !== null) {
                                    label += context.parsed;
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }

    function renderManHoursComparisonChart(data) {
        const ctx = document.getElementById('manHoursComparisonChart').getContext('2d');
        if (Chart.getChart(ctx)) {
            Chart.getChart(ctx).destroy();
        }

        const labels = data.map(item => item.role);
        const estimatedHours = data.map(item => item.estimated || 0);
        const actualHours = data.map(item => item.actual || 0);

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Estimated Man-hours',
                        data: estimatedHours,
                        backgroundColor: '#4299e1',
                        borderColor: '#3182ce',
                        borderWidth: 1,
                        borderRadius: 5,
                    },
                    {
                        label: 'Actual Man-hours',
                        data: actualHours,
                        backgroundColor: '#48bb78',
                        borderColor: '#38a169',
                        borderWidth: 1,
                        borderRadius: 5,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            font: {
                                family: 'Inter',
                                size: 14
                            },
                            color: '#475569'
                        }
                    },
                    title: {
                        display: false,
                        text: 'Estimated vs Actual Man-hours'
                    },
                    tooltip: {
                        callbacks: {
                            title: function(tooltipItems) {
                                const item = tooltipItems[0];
                                let label = item.chart.data.labels[item.dataIndex];
                                if (Array.isArray(label)) {
                                  return label.join(' ');
                                } else {
                                  return label;
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: { family: 'Inter', size: 12 },
                            color: '#64748b'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#e2e8f0'
                        },
                        ticks: {
                            font: { family: 'Inter', size: 12 },
                            color: '#64748b'
                        }
                    }
                }
            }
        });
    }

    fetchDashboardData();
});