const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Helper for generic API responses
async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  // Retrieve token from localStorage if available (fallback for clients not storing credentials in cookies)
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  
  const headers = new Headers(options.headers || {});
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  // Don't overwrite content-type if using FormData (e.g. for uploads)
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const mergedOptions: RequestInit = {
    ...options,
    headers,
    credentials: "include", // Essential for HttpOnly cookie exchange
  };

  const response = await fetch(url, mergedOptions);

  if (response.status === 204) {
    return null;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `Request failed with status ${response.status}`);
  }

  return data;
}

export const api = {
  // Auth
  async signup(email: string, password: string) {
    return fetchAPI("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  async login(formdata: FormData) {
    // Standard OAuth2 form-data payload for FastAPI OAuth2PasswordBearer
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      body: formdata,
      credentials: "include",
    });
    
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Authentication failed");
    }
    
    // Store in localStorage as fallback
    if (data.access_token && typeof window !== "undefined") {
      localStorage.setItem("token", data.access_token);
    }
    
    return data;
  },

  async logout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
    }
    return fetchAPI("/auth/logout", { method: "POST" });
  },

  async getMe() {
    return fetchAPI("/auth/me");
  },

  // Projects
  async listProjects() {
    return fetchAPI("/projects");
  },

  async createProject(project: {
    name: string;
    subject: string;
    course?: string;
    semester?: string;
    university?: string;
    preferred_language?: string;
  }) {
    return fetchAPI("/projects", {
      method: "POST",
      body: JSON.stringify(project),
    });
  },

  async getProject(projectId: string) {
    return fetchAPI(`/projects/${projectId}`);
  },

  async deleteProject(projectId: string) {
    return fetchAPI(`/projects/${projectId}`, {
      method: "DELETE",
    });
  },

  // Syllabus
  async uploadSyllabus(projectId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return fetchAPI(`/projects/syllabus/${projectId}/upload`, {
      method: "POST",
      body: formData,
    });
  },

  async confirmSyllabus(projectId: string, syllabusData: any) {
    return fetchAPI(`/projects/syllabus/${projectId}/confirm`, {
      method: "PUT",
      body: JSON.stringify(syllabusData),
    });
  },

  async getActiveSyllabus(projectId: string) {
    return fetchAPI(`/projects/syllabus/${projectId}/active`);
  },

  // Documents
  async listDocuments(projectId: string) {
    return fetchAPI(`/documents/${projectId}`);
  },

  async uploadDocument(projectId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return fetchAPI(`/documents/${projectId}/upload`, {
      method: "POST",
      body: formData,
    });
  },

  async getDocumentStatus(documentId: string) {
    return fetchAPI(`/documents/status/${documentId}`);
  },

  async deleteDocument(documentId: string) {
    return fetchAPI(`/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  // Notes
  async getNote(projectId: string, topicId: string) {
    return fetchAPI(`/notes/${projectId}/topic/${topicId}`);
  },

  async generateNote(projectId: string, topicId: string, mode: string = "detailed") {
    return fetchAPI(`/notes/${projectId}/topic/${topicId}/generate?mode=${mode}`, {
      method: "POST",
    });
  },

  async saveNote(projectId: string, topicId: string, content: string) {
    return fetchAPI(`/notes/${projectId}/topic/${topicId}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    });
  },

  async askTutor(projectId: string, message: string, history: { role: string, content: string }[]) {
    return fetchAPI(`/projects/tutor/${projectId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message, history }),
    });
  },
};
