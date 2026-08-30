const API_BASE_URL = "http://127.0.0.1:8000";

export async function fetchApi<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`);

  if (!response.ok) {
    throw new Error(
      `API request failed with status ${response.status}`
    );
  }

  return (await response.json()) as T;
}