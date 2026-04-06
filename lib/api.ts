const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://skillful-mercy-production-881f.up.railway.app";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("pixel_token");
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

// ========== Auth ==========

export async function register(email: string, password: string, name: string) {
  const res = await fetch(`${API_BASE}/users/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Registration failed");
  }
  const data = await res.json();
  localStorage.setItem("pixel_token", data.token);
  localStorage.setItem("pixel_user", JSON.stringify(data));
  return data;
}

export async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  localStorage.setItem("pixel_token", data.token);
  localStorage.setItem("pixel_user", JSON.stringify(data));
  return data;
}

export function logout() {
  localStorage.removeItem("pixel_token");
  localStorage.removeItem("pixel_user");
}

export function getStoredUser() {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("pixel_user");
  return raw ? JSON.parse(raw) : null;
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

// ========== Chat ==========

export async function chatWithPixel(
  message: string,
  userId: string = "web-demo"
): Promise<{ reply: string; engine: string }> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ message, user_id: userId }),
  });
  if (!res.ok) throw new Error(`Chat API error: ${res.status}`);
  return res.json();
}

export async function transcribeAudio(blob: Blob): Promise<{ text: string; language: string }> {
  const form = new FormData();
  form.append("file", blob, "recording.webm");
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/transcribe`, { method: "POST", headers, body: form });
  if (!res.ok) throw new Error(`Transcribe API error: ${res.status}`);
  return res.json();
}

export async function speakText(text: string, lang: string = "zh"): Promise<Blob> {
  const res = await fetch(`${API_BASE}/speak`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ text, lang }),
  });
  if (!res.ok) throw new Error(`Speak API error: ${res.status}`);
  return res.blob();
}

// ========== Conversations ==========

export async function getConversations(limit = 50) {
  const res = await fetch(`${API_BASE}/conversations?limit=${limit}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load conversations");
  return res.json();
}

export async function saveMessage(role: "user" | "pixel", content: string) {
  const res = await fetch(`${API_BASE}/conversations`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ role, content }),
  });
  if (!res.ok) throw new Error("Failed to save message");
  return res.json();
}

// ========== Notes ==========

export async function getNotes(limit = 50) {
  const res = await fetch(`${API_BASE}/notes?limit=${limit}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load notes");
  return res.json();
}

export async function getNote(id: string) {
  const res = await fetch(`${API_BASE}/notes/${id}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Note not found");
  return res.json();
}

export async function createNote(title: string, transcript: string, summary: string, keyPoints: string[]) {
  const res = await fetch(`${API_BASE}/notes`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ title, transcript, summary, key_points: keyPoints }),
  });
  if (!res.ok) throw new Error("Failed to create note");
  return res.json();
}

export async function deleteNote(id: string) {
  const res = await fetch(`${API_BASE}/notes/${id}`, { method: "DELETE", headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to delete note");
  return res.json();
}

// ========== Memories ==========

export async function getMemories(limit = 100) {
  const res = await fetch(`${API_BASE}/memories?limit=${limit}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load memories");
  return res.json();
}

export async function createMemory(content: string, category = "general") {
  const res = await fetch(`${API_BASE}/memories`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ content, category }),
  });
  if (!res.ok) throw new Error("Failed to create memory");
  return res.json();
}

export async function deleteMemory(id: string) {
  const res = await fetch(`${API_BASE}/memories/${id}`, { method: "DELETE", headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to delete memory");
  return res.json();
}

// ========== Summarize ==========

export async function summarize(transcript: string): Promise<{ summary: string; key_points: string[] }> {
  const res = await fetch(`${API_BASE}/summarize`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ transcript }),
  });
  if (!res.ok) throw new Error("Summarize failed");
  return res.json();
}

// ========== Soul ==========

export async function getSoul() {
  const res = await fetch(`${API_BASE}/soul`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load soul settings");
  return res.json();
}

export async function updateSoul(settings: Record<string, string>) {
  const res = await fetch(`${API_BASE}/soul`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error("Failed to update soul");
  return res.json();
}
