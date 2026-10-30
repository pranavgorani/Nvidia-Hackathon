export function getBaseUrl(): string {
  // If running on the server (SSR, Route handlers, or Next.js server components)
  if (typeof window === "undefined") {
    // In Vercel services mode, the service binding injects BACKEND_URL
    return process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }
  // In the browser:
  // If NEXT_PUBLIC_API_URL is explicitly set, use it.
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // Local development fallback if running on standard Next dev port without a reverse proxy rewrite
  if (window.location.hostname === "localhost" && window.location.port === "3000") {
    return "http://localhost:8000";
  }
  // Deployed / production relative path: rewrites route /api/(.*) directly to the backend service
  return "";
}

let cachedToken: string | null = null;
let cachedOrgId: string | null = null;

export function setAuthToken(token: string, orgId?: string) {
  cachedToken = token;
  if (orgId) cachedOrgId = orgId;
  if (typeof window !== "undefined") {
    localStorage.setItem("docuflow_token", token);
    if (orgId) localStorage.setItem("docuflow_org_id", orgId);
  }
}

export function getAuthToken(): string | null {
  if (cachedToken) return cachedToken;
  if (typeof window !== "undefined") {
    cachedToken = localStorage.getItem("docuflow_token");
  }
  return cachedToken;
}

export function getActiveOrgId(): string | null {
  if (cachedOrgId) return cachedOrgId;
  if (typeof window !== "undefined") {
    cachedOrgId = localStorage.getItem("docuflow_org_id");
  }
  return cachedOrgId;
}

async function request(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const orgId = getActiveOrgId();

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (orgId) {
    headers["X-Organization-Id"] = orgId;
  }

  // Only set Content-Type if not FormData
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Unknown error occurred" }));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export const api = {
  auth: {
    login: async (email: string, password: string) => {
      const data = await request("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setAuthToken(data.access_token, data.active_organization_id);
      return data;
    },
    register: async (email: string, fullName: string, password: string, orgName: string) => {
      const data = await request("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, full_name: fullName, password, organization_name: orgName }),
      });
      setAuthToken(data.access_token, data.active_organization_id);
      return data;
    },
    getMe: () => request("/api/auth/me"),
  },
  dashboard: {
    getMetrics: () => request("/api/dashboard/metrics"),
  },
  crm: {
    getLeads: (status?: string, search?: string) => {
      const params = new URLSearchParams();
      if (status) params.append("status", status);
      if (search) params.append("search", search);
      return request(`/api/crm/leads?${params.toString()}`);
    },
    createLead: (data: any) => request("/api/crm/leads", { method: "POST", body: JSON.stringify(data) }),
    getLead: (leadId: string) => request(`/api/crm/leads/${leadId}`),
    updateLead: (leadId: string, data: any) => request(`/api/crm/leads/${leadId}`, { method: "PUT", body: JSON.stringify(data) }),
    getProperties: () => request("/api/crm/properties"),
    getTasks: (status?: string) => request(`/api/crm/tasks${status ? `?status=${status}` : ""}`),
    createTask: (data: any) => request("/api/crm/tasks", { method: "POST", body: JSON.stringify(data) }),
    updateTaskStatus: (taskId: string, status: string) => request(`/api/crm/tasks/${taskId}/status?status=${status}`, { method: "PUT" }),
    addLeadNote: (leadId: string, content: string) =>
      request(`/api/crm/leads/${leadId}/notes`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
  },
  documents: {
    upload: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request("/api/documents/upload", { method: "POST", body: formData });
    },
    list: (status?: string) => request(`/api/documents${status ? `?status=${status}` : ""}`),
    get: (id: string) => request(`/api/documents/${id}`),
    process: (id: string) => request(`/api/documents/${id}/process`, { method: "POST" }),
    getExtraction: (id: string) => request(`/api/documents/${id}/extraction`),
    reviewExtraction: (id: string, updatedFields: any, reason?: string) =>
      request(`/api/documents/extractions/${id}/review`, {
        method: "PUT",
        body: JSON.stringify({ updated_fields: updatedFields, change_reason: reason }),
      }),
  },
  agent: {
    run: (instruction: string, skillId?: string, documentId?: string, contextData?: any) =>
      request("/api/agent/run", {
        method: "POST",
        body: JSON.stringify({
          instruction,
          skill_id: skillId || "property_intake_agent",
          document_id: documentId,
          context_data: contextData,
        }),
      }),
    getWorkflows: (status?: string) => request(`/api/agent/workflows${status ? `?status=${status}` : ""}`),
    getWorkflow: (id: string) => request(`/api/agent/workflows/${id}`),
  },
  approvals: {
    list: (status?: string) => request(`/api/approvals${status ? `?status=${status}` : ""}`),
    get: (id: string) => request(`/api/approvals/${id}`),
    decide: (id: string, decision: "approve" | "reject", notes?: string) =>
      request(`/api/approvals/${id}/decide`, {
        method: "POST",
        body: JSON.stringify({ decision, notes }),
      }),
  },
  skills: {
    list: () => request("/api/skills"),
    get: (id: string) => request(`/api/skills/${id}`),
  },
  audit: {
    getLogs: (actionType?: string) => request(`/api/audit/logs${actionType ? `?action_type=${actionType}` : ""}`),
  },
};
