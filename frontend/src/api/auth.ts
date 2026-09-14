import { apiRequest } from "./client";

export type UserRole = "student" | "faculty" | "admin";

export interface User {
  id: number;
  name: string;
  roll_number: string | null;
  email: string;
  role: UserRole;
  storage_limit: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterPayload {
  name: string;
  roll_number: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export function register(payload: RegisterPayload): Promise<User> {
  // Backend treats an empty roll number as "not provided".
  const body = { ...payload, roll_number: payload.roll_number || null };
  return apiRequest<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function login(payload: LoginPayload): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchCurrentUser(token: string): Promise<User> {
  return apiRequest<User>("/users/me", { method: "GET" }, token);
}
