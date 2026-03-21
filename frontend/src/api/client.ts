const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(0, 'Could not connect to the server');
  }

  if (!response.ok) {
    if (response.status === 404) {
      throw new ApiError(404, 'Not found');
    }
    if (response.status === 422) {
      throw new ApiError(422, 'Invalid search parameters');
    }
    throw new ApiError(response.status, `Server error (${response.status})`);
  }

  return response.json() as Promise<T>;
}
