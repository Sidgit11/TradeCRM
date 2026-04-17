const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiResponse<T> {
  data: T;
  status: number;
}

interface ApiError {
  detail: string;
  status: number;
}

type GetTokenFn = () => Promise<string | null>;

class ApiClient {
  private baseUrl: string;
  private _getToken: GetTokenFn | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setTokenProvider(fn: GetTokenFn) {
    this._getToken = fn;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<ApiResponse<T>> {
    const token = this._getToken ? await this._getToken() : null;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw { detail: "Unauthorized", status: 401 } satisfies ApiError;
    }

    if (response.status === 402) {
      throw { detail: "Upgrade required", status: 402 } satisfies ApiError;
    }

    if (response.status === 429) {
      throw { detail: "Rate limit exceeded", status: 429 } satisfies ApiError;
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw { detail: error.detail || "Request failed", status: response.status } satisfies ApiError;
    }

    // 204 No Content has no body
    if (response.status === 204) {
      return { data: undefined as unknown as T, status: 204 };
    }

    const data = await response.json();
    return { data, status: response.status };
  }

  async get<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path);
  }

  async post<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async put<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path, { method: "DELETE" });
  }
}

export const api = new ApiClient(API_BASE_URL);

/** Extract a human-readable error message from a caught API error. */
export function getErrorMessage(err: unknown, fallback: string = "Something went wrong"): string {
  if (err && typeof err === "object" && "detail" in err) {
    return (err as ApiError).detail || fallback;
  }
  if (err instanceof Error) {
    return err.message || fallback;
  }
  return fallback;
}
