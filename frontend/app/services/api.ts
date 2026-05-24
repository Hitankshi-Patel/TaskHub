const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export interface TaskData {
  id: string;
  title: string;
  description: string;
  product_image_url: string;
  status: 'pending' | 'assigned' | 'in_progress' | 'submitted' | 'accepted' | 'revision_requested';
  assigned_to: string | null;
  created_by: string;
  feedback: string | null;
  created_at: string;
  updated_at: string;
  assignee_name?: string;
}

export interface GeneratedImage {
  id: string;
  task_id: string;
  image_type: string;
  image_url: string;
  prompt_used: string | null;
  angle: string | null;
  is_final: boolean;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: 'admin' | 'user';
}

export interface Analytics {
  totals: {
    users: number;
    tasks: number;
    generations: number;
  };
  statuses: {
    pending: number;
    assigned: number;
    in_progress: number;
    submitted: number;
    accepted: number;
    revision_requested: number;
  };
  recent_activity: Array<{
    id: string;
    action: string;
    table_name: string;
    user_email: string;
    created_at: string;
  }>;
}

// Request Wrapper
async function request<T>(
  path: string, 
  method: string = 'GET', 
  body: any = null, 
  headers: Record<string, string> = {}
): Promise<T> {
  const options: RequestInit = {
    method,
    headers: {
      ...headers
    }
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const res = await fetch(`${API_URL}${path}`, options);
  
  if (!res.ok) {
    let errMsg = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const errorData = await res.json();
      errMsg = errorData.error || errMsg;
    } catch (e) {
      // Ignored
    }
    throw new Error(errMsg);
  }

  return res.json() as Promise<T>;
}

// API Service Functions
export const api = {
  // Users (Admin)
  getUsers: (headers: Record<string, string>) => 
    request<User[]>('/api/auth/users', 'GET', null, headers),

  // Tasks - Admin
  createTask: (data: { title: string; description?: string; product_image_url: string; assigned_to?: string }, headers: Record<string, string>) =>
    request<TaskData>('/api/tasks', 'POST', data, headers),
    
  listAllTasks: (headers: Record<string, string>) =>
    request<TaskData[]>('/api/tasks', 'GET', null, headers),
    
  assignTask: (id: string, assignedTo: string, headers: Record<string, string>) =>
    request<TaskData>(`/api/tasks/${id}/assign`, 'POST', { assigned_to: assignedTo }, headers),
    
  acceptTask: (id: string, feedback: string, headers: Record<string, string>) =>
    request<TaskData>(`/api/tasks/${id}/accept`, 'PUT', { feedback }, headers),
    
  requestRevision: (id: string, feedback: string, headers: Record<string, string>) =>
    request<TaskData>(`/api/tasks/${id}/request-revision`, 'PUT', { feedback }, headers),
    
  deleteTask: (id: string, headers: Record<string, string>) =>
    request<{ message: string }>(`/api/tasks/${id}`, 'DELETE', null, headers),

  // Tasks - User
  getMyTasks: (headers: Record<string, string>) =>
    request<TaskData[]>('/api/my-tasks', 'GET', null, headers),
    
  getTaskDetails: (id: string, headers: Record<string, string>) =>
    request<TaskData>(`/api/tasks/${id}`, 'GET', null, headers),
    
  startTask: (id: string, headers: Record<string, string>) =>
    request<TaskData>(`/api/tasks/${id}/start`, 'PUT', null, headers),
    
  submitTask: (id: string, headers: Record<string, string>) =>
    request<TaskData>(`/api/tasks/${id}/submit`, 'POST', null, headers),

  // AI Generations
  generateImage: (taskId: string, data: { image_type: string; angle?: string }, headers: Record<string, string>) =>
    request<{ job_id: string; status: string; message: string }>(`/api/tasks/${taskId}/generate`, 'POST', data, headers),
    
  getJobStatus: (jobId: string, headers: Record<string, string>) =>
    request<{ status: 'pending' | 'running' | 'completed' | 'failed'; result?: GeneratedImage; error?: string; progress: number }>(`/api/jobs/${jobId}/status`, 'GET', null, headers),
    
  getTaskGenerations: (taskId: string, headers: Record<string, string>) =>
    request<GeneratedImage[]>(`/api/tasks/${taskId}/generations`, 'GET', null, headers),
    
  deleteGeneration: (id: string, headers: Record<string, string>) =>
    request<{ message: string }>(`/api/generations/${id}`, 'DELETE', null, headers),

  // Analytics (Admin)
  getAnalytics: (headers: Record<string, string>) =>
    request<Analytics>('/api/admin/analytics', 'GET', null, headers)
};
export default api;
