const API_BASE = '/api/v1'

export interface Workflow {
  workflow_id: string
  name: string
  description: string
  tasks: Task[]
  config: Record<string, any>
  created_at: string
}

export interface Task {
  task_id: string
  agent_type: string
  config: Record<string, any>
  dependencies: string[]
}

export interface Execution {
  execution_id: string
  workflow_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  input_data: Record<string, any>
  priority: number
  task_statuses: TaskStatus[]
  started_at?: string
  completed_at?: string
  error?: string
  result?: Record<string, any>
  created_at: string
}

export interface TaskStatus {
  task_id: string
  status: string
  started_at?: string
  completed_at?: string
  error?: string
  result?: Record<string, any>
}

export interface Metrics {
  total_workflows: number
  total_executions: number
  success_rate: number
  avg_execution_time: number
  active_executions: number
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  components: Record<string, any>
  timestamp: string
}

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        error: 'Request failed',
        message: response.statusText,
      }))
      throw new Error(error.message || 'Request failed')
    }

    return response.json()
  }

  // Workflows
  async getWorkflows(): Promise<Workflow[]> {
    return this.request('/workflows')
  }

  async getWorkflow(id: string): Promise<Workflow> {
    return this.request(`/workflows/${id}`)
  }

  async createWorkflow(workflow: Partial<Workflow>): Promise<Workflow> {
    return this.request('/workflows', {
      method: 'POST',
      body: JSON.stringify(workflow),
    })
  }

  async deleteWorkflow(id: string): Promise<void> {
    return this.request(`/workflows/${id}`, { method: 'DELETE' })
  }

  // Executions
  async getExecutions(params?: {
    workflow_id?: string
    status?: string
  }): Promise<Execution[]> {
    const query = new URLSearchParams(params as any).toString()
    return this.request(`/executions${query ? `?${query}` : ''}`)
  }

  async getExecution(id: string): Promise<Execution> {
    return this.request(`/executions/${id}`)
  }

  async createExecution(data: {
    workflow_id: string
    input_data?: Record<string, any>
    priority?: number
  }): Promise<Execution> {
    return this.request('/executions', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async cancelExecution(id: string): Promise<Execution> {
    return this.request(`/executions/${id}/cancel`, { method: 'POST' })
  }

  async deleteExecution(id: string): Promise<void> {
    return this.request(`/executions/${id}`, { method: 'DELETE' })
  }

  // Metrics
  async getMetrics(): Promise<Metrics> {
    return this.request('/metrics')
  }

  // Health
  async getHealth(): Promise<HealthStatus> {
    return this.request('/health')
  }
}

export const api = new ApiService()
