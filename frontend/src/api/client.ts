import axios, { type AxiosError } from "axios";
import { fetchAuthSession } from "aws-amplify/auth";

const baseURL = import.meta.env.VITE_API_URL || "/api";

export const apiClient = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use(async (config) => {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // not signed in — let request go (will get 401 from API GW)
  }
  return config;
});

export interface ApiError {
  status: number;
  error?: string;
  message: string;
  details?: Record<string, unknown>;
}

export function toApiError(err: unknown): ApiError {
  const ax = err as AxiosError<{ error?: string; message?: string; details?: Record<string, unknown> }>;
  if (ax.response) {
    return {
      status: ax.response.status,
      error: ax.response.data?.error,
      message: ax.response.data?.message ?? ax.message ?? "Greška",
      details: ax.response.data?.details,
    };
  }
  return { status: 0, message: (err as Error)?.message ?? "Greška" };
}
