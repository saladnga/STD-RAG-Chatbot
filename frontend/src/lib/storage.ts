import { signOut } from "firebase/auth";
import { auth } from "./firebase";

const SESSION_ID_KEY = "current_session_id";

export interface User {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  has_custom_openai_key?: boolean;
  openai_model?: string | null;
  [key: string]: unknown;
}

// Waits for Firebase to restore the login on page load; getIdToken refreshes the token if it's about to expire.
export const getToken = async () => {
  await auth.authStateReady();
  return (await auth.currentUser?.getIdToken()) ?? null;
};

export const getUser = () => {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
};

export const saveUser = (user: User) =>
  localStorage.setItem("user", JSON.stringify(user));

export const saveSession = (user: User) => {
  saveUser(user);
  // A fresh login should never auto-resume whatever chat was last active - especially not another user's, on a shared browser that never logged out.
  clearCurrentSessionId();
};

export const getCurrentSessionId = () => localStorage.getItem(SESSION_ID_KEY);

export const setCurrentSessionId = (id: string) =>
  localStorage.setItem(SESSION_ID_KEY, id);

export const clearCurrentSessionId = () =>
  localStorage.removeItem(SESSION_ID_KEY);

export const clearAuth = () => {
  void signOut(auth);
  localStorage.removeItem("user");
  clearCurrentSessionId();
};
