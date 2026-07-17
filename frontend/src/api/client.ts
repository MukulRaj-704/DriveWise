import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({ baseURL: API_BASE_URL });

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ---------- Types ----------

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface BrochureOut {
  id: string;
  file_name: string;
  car_name: string | null;
  manufacturer: string | null;
  year: string | null;
  page_count: number;
  status: "processing" | "ready" | "failed";
  created_at: string;
}

export interface SourceAttribution {
  chunk_id: string;
  brochure_id: string;
  brochure_name: string;
  page: number | null;
  section: string | null;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  sources: SourceAttribution[];
}

export interface ChatSessionOut {
  id: string;
  title: string;
  created_at: string;
}

export interface ChatMessageOut {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceAttribution[] | null;
  created_at: string;
}

// ---------- API calls ----------

export const authApi = {
  register: (data: { email: string; full_name: string; password: string }) =>
    apiClient.post<UserOut>("/auth/register", data),
  login: (data: { email: string; password: string }) => apiClient.post<TokenPair>("/auth/login", data),
};

export const brochureApi = {
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post<BrochureOut>("/brochure/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  list: () => apiClient.get<{ brochures: BrochureOut[]; total: number }>("/brochure"),
  remove: (id: string) => apiClient.delete(`/brochure/${id}`),
};

export const chatApi = {
  ask: (data: { message: string; session_id?: string; brochure_ids?: string[]; filters?: Record<string, string> }) =>
    apiClient.post<ChatResponse>("/chat", data),
  history: () => apiClient.get<{ sessions: ChatSessionOut[] }>("/chat/history"),
  session: (id: string) => apiClient.get<{ id: string; title: string; created_at: string; messages: ChatMessageOut[] }>(`/chat/${id}`),
  remove: (id: string) => apiClient.delete(`/chat/${id}`),
};
