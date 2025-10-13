// API Base URL
const API_BASE = '/api/v1';

// Auto-refresh interval
let autoRefreshInterval = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    // Check health on load
    checkHealth();
    setInterval(checkHealth, 30000); // Check every 30 seconds

    // Load initial data
    showTab('workflows');
    loadWorkflows();

    // Setup create workflow form
    document.getElementById('create-workflow-form').addEventListener('submit', handleCreateWorkflow);

    // Setup auto-refresh for executions
    document.getElementById('auto-refresh').addEventListener('change', (e) => {
        if (e.target.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
});

// Tab Management
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.add('hidden');
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('border-blue-600', 'text-blue-600');
        btn.classList.add('border-transparent', 'text-gray-500');
    });

    // Show selected tab
    document.getElementById(`content-${tabName}`).classList.remove('hidden');

    // Add active class to button
    const activeBtn = document.getElementById(`tab-${tabName}`);
    activeBtn.classList.remove('border-transparent', 'text-gray-500');
    activeBtn.classList.add('border-blue-600', 'text-blue-600');

    // Load data for tab
    if (tabName === 'workflows') {
        loadWorkflows();
        stopAutoRefresh();
    } else if (tabName === 'executions') {
        loadExecutions();
        if (document.getElementById('auto-refresh').checked) {
            startAutoRefresh();
        }
    } else if (tabName === 'metrics') {
        loadMetrics();
        stopAutoRefresh();
    }
}

// Health Check
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        const indicator = document.getElementById('health-indicator');
        const status = document.getElementById('health-status');

        if (data.status === 'healthy') {
            indicator.className = 'w-3 h-3 rounded-full bg-green-500';
            status.textContent = 'Healthy';
            status.className = 'text-sm text-green-600';
        } else if (data.status === 'degraded') {
            indicator.className = 'w-3 h-3 rounded-full bg-yellow-500';
            status.textContent = 'Degraded';
            status.className = 'text-sm text-yellow-600';
        } else {
            indicator.className = 'w-3 h-3 rounded-full bg-red-500 animate-pulse-slow';
            status.textContent = 'Unhealthy';
            status.className = 'text-sm text-red-600';
        }
    } catch (error) {
        const indicator = document.getElementById('health-indicator');
        const status = document.getElementById('health-status');
        indicator.className = 'w-3 h-3 rounded-full bg-red-500 animate-pulse-slow';
        status.textContent = 'Error';
        status.className = 'text-sm text-red-600';
    }
}

// Workflows
async function loadWorkflows() {
    const container = document.getElementById('workflows-list');
    container.innerHTML = '<div class="text-center py-12 text-gray-500"><i class="fas fa-spinner fa-spin text-4xl mb-4"></i><p>Loading workflows...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/workflows`);
        const workflows = await response.json();

        if (workflows.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12">
                    <i class="fas fa-folder-open text-gray-400 text-6xl mb-4"></i>
                    <p class="text-gray-500 mb-4">No workflows yet</p>
                    <button onclick="showCreateWorkflowModal()" class="text-blue-600 hover:text-blue-700 font-medium">
                        <i class="fas fa-plus mr-2"></i>Create your first workflow
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = workflows.map(wf => `
            <div class="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow">
                <div class="flex justify-between items-start mb-4">
                    <div class="flex-1">
                        <h3 class="text-lg font-semibold text-gray-900 mb-1">${escapeHtml(wf.name)}</h3>
                        ${wf.description ? `<p class="text-sm text-gray-600 mb-3">${escapeHtml(wf.description)}</p>` : ''}
                        <div class="flex items-center space-x-4 text-sm text-gray-500">
                            <span><i class="fas fa-tasks mr-1"></i>${wf.tasks.length} tasks</span>
                            <span><i class="fas fa-calendar mr-1"></i>${formatDate(wf.created_at)}</span>
                        </div>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="startExecution('${wf.workflow_id}')" class="text-green-600 hover:text-green-700 px-3 py-1 border border-green-600 rounded-md text-sm font-medium hover:bg-green-50">
                            <i class="fas fa-play mr-1"></i>Run
                        </button>
                        <button onclick="deleteWorkflow('${wf.workflow_id}')" class="text-red-600 hover:text-red-700 px-3 py-1 border border-red-600 rounded-md text-sm font-medium hover:bg-red-50">
                            <i class="fas fa-trash mr-1"></i>Delete
                        </button>
                    </div>
                </div>
                <details class="mt-4">
                    <summary class="cursor-pointer text-sm text-blue-600 hover:text-blue-700 font-medium">
                        <i class="fas fa-chevron-down mr-1"></i>View Tasks
                    </summary>
                    <div class="mt-3 space-y-2">
                        ${wf.tasks.map(task => `
                            <div class="bg-gray-50 rounded p-3 text-sm">
                                <div class="font-medium text-gray-900">${escapeHtml(task.task_id)}</div>
                                <div class="text-gray-600 mt-1">${escapeHtml(task.prompt)}</div>
                                ${task.dependencies.length > 0 ? `<div class="text-xs text-gray-500 mt-1">Depends on: ${task.dependencies.join(', ')}</div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </details>
            </div>
        `).join('');

    } catch (error) {
        container.innerHTML = `
            <div class="text-center py-12 text-red-600">
                <i class="fas fa-exclamation-circle text-4xl mb-4"></i>
                <p>Error loading workflows</p>
                <p class="text-sm mt-2">${error.message}</p>
            </div>
        `;
    }
}

async function deleteWorkflow(workflowId) {
    if (!confirm('Are you sure you want to delete this workflow?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/workflows/${workflowId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('Workflow deleted successfully', 'success');
            loadWorkflows();
        } else {
            throw new Error('Failed to delete workflow');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function startExecution(workflowId) {
    try {
        const response = await fetch(`${API_BASE}/executions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                workflow_id: workflowId,
                input_data: {},
                priority: 5
            })
        });

        if (response.ok) {
            const execution = await response.json();
            showToast('Execution started successfully', 'success');
            showTab('executions');
        } else {
            throw new Error('Failed to start execution');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Executions
async function loadExecutions() {
    const container = document.getElementById('executions-list');
    container.innerHTML = '<div class="text-center py-12 text-gray-500"><i class="fas fa-spinner fa-spin text-4xl mb-4"></i><p>Loading executions...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/executions`);
        const executions = await response.json();

        if (executions.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12">
                    <i class="fas fa-play-circle text-gray-400 text-6xl mb-4"></i>
                    <p class="text-gray-500 mb-4">No executions yet</p>
                    <button onclick="showTab('workflows')" class="text-blue-600 hover:text-blue-700 font-medium">
                        <i class="fas fa-arrow-left mr-2"></i>Go to workflows to start one
                    </button>
                </div>
            `;
            return;
        }

        // Sort by created_at descending
        executions.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        container.innerHTML = executions.map(exec => {
            const statusConfig = getStatusConfig(exec.status);
            return `
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex justify-between items-start">
                        <div class="flex-1">
                            <div class="flex items-center mb-2">
                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusConfig.class}">
                                    <i class="${statusConfig.icon} mr-1"></i>${exec.status}
                                </span>
                                <span class="ml-3 text-sm text-gray-500">Priority: ${exec.priority}</span>
                            </div>
                            <p class="text-sm text-gray-600 mb-2">
                                <i class="fas fa-fingerprint mr-1"></i>Execution ID: <span class="font-mono text-xs">${exec.execution_id}</span>
                            </p>
                            <p class="text-sm text-gray-600 mb-2">
                                <i class="fas fa-project-diagram mr-1"></i>Workflow ID: <span class="font-mono text-xs">${exec.workflow_id}</span>
                            </p>
                            <div class="text-xs text-gray-500 mt-3">
                                <span>Created: ${formatDate(exec.created_at)}</span>
                                ${exec.started_at ? ` | Started: ${formatDate(exec.started_at)}` : ''}
                                ${exec.completed_at ? ` | Completed: ${formatDate(exec.completed_at)}` : ''}
                            </div>
                        </div>
                        <div class="flex space-x-2">
                            ${exec.status === 'pending' || exec.status === 'running' ? `
                                <button onclick="cancelExecution('${exec.execution_id}')" class="text-orange-600 hover:text-orange-700 px-3 py-1 border border-orange-600 rounded-md text-sm font-medium hover:bg-orange-50">
                                    <i class="fas fa-stop mr-1"></i>Cancel
                                </button>
                            ` : ''}
                            <button onclick="deleteExecution('${exec.execution_id}')" class="text-red-600 hover:text-red-700 px-3 py-1 border border-red-600 rounded-md text-sm font-medium hover:bg-red-50">
                                <i class="fas fa-trash mr-1"></i>Delete
                            </button>
                        </div>
                    </div>
                    ${exec.error ? `
                        <div class="mt-4 bg-red-50 border border-red-200 rounded p-3">
                            <p class="text-sm text-red-800"><i class="fas fa-exclamation-triangle mr-1"></i>${escapeHtml(exec.error)}</p>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

    } catch (error) {
        container.innerHTML = `
            <div class="text-center py-12 text-red-600">
                <i class="fas fa-exclamation-circle text-4xl mb-4"></i>
                <p>Error loading executions</p>
                <p class="text-sm mt-2">${error.message}</p>
            </div>
        `;
    }
}

async function cancelExecution(executionId) {
    try {
        const response = await fetch(`${API_BASE}/executions/${executionId}/cancel`, {
            method: 'POST'
        });

        if (response.ok) {
            showToast('Execution cancelled', 'success');
            loadExecutions();
        } else {
            throw new Error('Failed to cancel execution');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function deleteExecution(executionId) {
    if (!confirm('Are you sure you want to delete this execution?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/executions/${executionId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('Execution deleted', 'success');
            loadExecutions();
        } else {
            throw new Error('Failed to delete execution');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Metrics
async function loadMetrics() {
    try {
        const response = await fetch(`${API_BASE}/metrics/summary`);
        const metrics = await response.json();

        // Update metric cards
        document.getElementById('metric-workflows').textContent = metrics.total_workflows;
        document.getElementById('metric-executions').textContent = metrics.total_executions;
        document.getElementById('metric-avg-time').textContent = metrics.avg_execution_time_seconds.toFixed(1);

        // Calculate success rate
        const total = metrics.total_executions;
        const completed = metrics.executions_by_status.completed || 0;
        const successRate = total > 0 ? ((completed / total) * 100).toFixed(1) : '0.0';
        document.getElementById('metric-success-rate').textContent = `${successRate}%`;

        // Status breakdown
        const statusContainer = document.getElementById('status-breakdown');
        const statuses = [
            { name: 'Completed', key: 'completed', color: 'green' },
            { name: 'Running', key: 'running', color: 'blue' },
            { name: 'Pending', key: 'pending', color: 'yellow' },
            { name: 'Failed', key: 'failed', color: 'red' },
            { name: 'Cancelled', key: 'cancelled', color: 'gray' }
        ];

        statusContainer.innerHTML = statuses.map(status => {
            const count = metrics.executions_by_status[status.key] || 0;
            const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;

            return `
                <div>
                    <div class="flex justify-between text-sm mb-1">
                        <span class="text-gray-700 font-medium">${status.name}</span>
                        <span class="text-gray-600">${count} (${percentage}%)</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-${status.color}-500 h-2 rounded-full" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        showToast(`Error loading metrics: ${error.message}`, 'error');
    }
}

// Auto-refresh
function startAutoRefresh() {
    if (autoRefreshInterval) return;
    autoRefreshInterval = setInterval(() => {
        const activeTab = document.querySelector('.tab-button.border-blue-600').id.replace('tab-', '');
        if (activeTab === 'executions') {
            loadExecutions();
        }
    }, 5000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Modal
function showCreateWorkflowModal() {
    document.getElementById('create-workflow-modal').classList.remove('hidden');
}

function closeCreateWorkflowModal() {
    document.getElementById('create-workflow-modal').classList.add('hidden');
    document.getElementById('create-workflow-form').reset();
}

async function handleCreateWorkflow(e) {
    e.preventDefault();

    const name = document.getElementById('workflow-name').value;
    const description = document.getElementById('workflow-description').value;
    const tasksText = document.getElementById('workflow-tasks').value;

    try {
        const tasks = JSON.parse(tasksText);

        const response = await fetch(`${API_BASE}/workflows`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                description: description || null,
                tasks
            })
        });

        if (response.ok) {
            showToast('Workflow created successfully', 'success');
            closeCreateWorkflowModal();
            loadWorkflows();
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create workflow');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const icon = document.getElementById('toast-icon');
    const msg = document.getElementById('toast-message');

    const icons = {
        success: '<i class="fas fa-check-circle text-green-500 text-xl"></i>',
        error: '<i class="fas fa-exclamation-circle text-red-500 text-xl"></i>',
        info: '<i class="fas fa-info-circle text-blue-500 text-xl"></i>'
    };

    icon.innerHTML = icons[type] || icons.info;
    msg.textContent = message;

    toast.classList.remove('hidden');
    setTimeout(() => {
        hideToast();
    }, 5000);
}

function hideToast() {
    document.getElementById('toast').classList.add('hidden');
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function getStatusConfig(status) {
    const configs = {
        pending: { icon: 'fas fa-clock', class: 'bg-yellow-100 text-yellow-800' },
        running: { icon: 'fas fa-spinner fa-spin', class: 'bg-blue-100 text-blue-800' },
        completed: { icon: 'fas fa-check-circle', class: 'bg-green-100 text-green-800' },
        failed: { icon: 'fas fa-times-circle', class: 'bg-red-100 text-red-800' },
        cancelled: { icon: 'fas fa-ban', class: 'bg-gray-100 text-gray-800' }
    };
    return configs[status] || configs.pending;
}
