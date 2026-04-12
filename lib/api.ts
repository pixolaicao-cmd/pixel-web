// Same-origin: API lives at /api/* in the same Vercel deployment
// Override with NEXT_PUBLIC_API_URL for local dev pointing to Railway or local backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

// ── Token storage helpers ──────────────────────────────────
// remember_me=true  → localStorage  (跨 session 持久)
// remember_me=false → sessionStorage（关闭浏览器即清除）

/** 解码 JWT payload，不做验证（签名在服务端验） */
function decodeTokenExp(token: string): number | null {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(b64));
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("pixel_token") ?? sessionStorage.getItem("pixel_token");
}

/** token 存在 + 未过期 */
export function isTokenValid(): boolean {
  const token = getToken();
  if (!token) return false;
  const exp = decodeTokenExp(token);
  if (exp !== null && Date.now() > exp) {
    // 已过期，清理
    logout();
    return false;
  }
  return true;
}

/** 兼容旧调用 */
export function isLoggedIn(): boolean {
  return isTokenValid();
}

function storeAuth(data: { token: string; remember_me?: boolean } & Record<string, unknown>, rememberMe = true) {
  const storage = rememberMe ? localStorage : sessionStorage;
  const other   = rememberMe ? sessionStorage : localStorage;
  // 清掉另一个 storage 里的旧 token（避免混淆）
  other.removeItem("pixel_token");
  other.removeItem("pixel_user");
  storage.setItem("pixel_token", data.token);
  storage.setItem("pixel_user", JSON.stringify(data));
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
  storeAuth(data, true); // 注册默认记住
  return data;
}

export async function login(email: string, password: string, rememberMe = true) {
  const res = await fetch(`${API_BASE}/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, remember_me: rememberMe }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  storeAuth(data, rememberMe);
  return data;
}

/** Google OAuth：跳转到后端 authorize 入口 */
export function loginWithGoogle() {
  window.location.href = `${API_BASE}/users/google/authorize`;
}

/**
 * Google OAuth 回调页面（/auth/callback）用这个函数把 URL 参数写入 localStorage。
 * 返回 true 表示成功写入。
 */
export function consumeOAuthCallback(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (!token) return false;
  const data = {
    token,
    user_id:    params.get("user_id") ?? "",
    email:      params.get("email")   ?? "",
    name:       params.get("name")    ?? "",
    remember_me: true,
  };
  storeAuth(data, true);
  return true;
}

export function logout() {
  localStorage.removeItem("pixel_token");
  localStorage.removeItem("pixel_user");
  sessionStorage.removeItem("pixel_token");
  sessionStorage.removeItem("pixel_user");
}

export function getStoredUser() {
  if (typeof window === "undefined") return null;
  const raw =
    localStorage.getItem("pixel_user") ?? sessionStorage.getItem("pixel_user");
  return raw ? JSON.parse(raw) : null;
}

// ========== Chat ==========

export async function chatWithPixel(
  message: string,
  userId: string = "web-demo"
): Promise<{ reply: string; engine: string }> {
  // /ui/chat: auto-saves conversation + auto-extracts memories (requires auth)
  // falls back to /chat if not logged in
  const token = getToken();
  if (token) {
    const res = await fetch(`${API_BASE}/ui/chat`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ message }),
    });
    if (res.ok) return res.json();
  }
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

export async function createNote(title: string, transcript: string, summary: string, keyPoints: string[], markdown?: string) {
  const res = await fetch(`${API_BASE}/notes`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ title, transcript, summary, key_points: keyPoints, markdown }),
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
    body: JSON.stringify({ transcript, mode: "summary" }),
  });
  if (!res.ok) throw new Error("Summarize failed");
  return res.json();
}

export async function summarizeDocument(transcript: string): Promise<{ summary: string; key_points: string[]; markdown: string }> {
  const res = await fetch(`${API_BASE}/summarize`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ transcript, mode: "document" }),
  });
  if (!res.ok) throw new Error("Document summarize failed");
  return res.json();
}

// ========== Devices ==========

export async function getDevices() {
  const res = await fetch(`${API_BASE}/devices`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load devices");
  return res.json() as Promise<{ devices: Device[] }>;
}

export async function unlinkDevice(deviceId: string) {
  const res = await fetch(`${API_BASE}/devices/${encodeURIComponent(deviceId)}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to unlink device");
  return res.json();
}

export interface Device {
  id: string;
  device_id: string;           // MAC address
  model: string;
  firmware_version: string;
  paired_at: string | null;
  last_seen_at: string | null;
  created_at: string;
}

// ========== Note Export ==========

/** 触发文件下载（DOCX / TXT） */
async function _downloadNote(noteId: string, format: "docx" | "txt") {
  const res = await fetch(`${API_BASE}/notes/${noteId}/export/${format}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") ?? "";
  const match = cd.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)/i);
  const filename = match ? decodeURIComponent(match[1]) : `note.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const exportNoteDocx = (id: string) => _downloadNote(id, "docx");
export const exportNoteTxt  = (id: string) => _downloadNote(id, "txt");

/** 打开打印/PDF 页（新标签页，用户 Ctrl+P 保存为 PDF） */
export function exportNotePrint(id: string) {
  window.open(`${API_BASE}/notes/${id}/export/print`, "_blank");
}

// ========== File Import ==========

export async function importFileToMemory(
  file: File,
  category = "document",
): Promise<{ memory_ids: string[]; chunks: number; total_chars: number; preview: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("category", category);
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/memories/import`, { method: "POST", headers, body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || `Import failed: ${res.status}`);
  }
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
