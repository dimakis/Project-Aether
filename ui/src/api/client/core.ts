import { env } from "@/lib/env";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${env.API_URL}/v1${path}`;
  const response = await fetch(url, {
    ...options,
    credentials: "include", // Send httpOnly JWT cookie
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  // Redirect to login on 401 (expired session, etc.)
  if (response.status === 401 && !path.startsWith("/auth/")) {
    window.location.href = "/login";
    throw new ApiError(401, "Session expired");
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message =
      body?.error?.message || body?.detail || response.statusText;
    throw new ApiError(response.status, message);
  }

  // 204 No Content has no body to parse
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
