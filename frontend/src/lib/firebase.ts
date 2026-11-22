import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const app = initializeApp({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
});

// Firebase keeps the login in the browser and refreshes the 1-hour token on its own.
export const auth = getAuth(app);

const AUTH_ERRORS: Record<string, string> = {
  "auth/email-already-in-use": "An account with this email already exists.",
  "auth/invalid-credential": "Wrong email or password.",
  "auth/invalid-email": "That email address isn't valid.",
  "auth/weak-password": "That password is too weak.",
  "auth/too-many-requests": "Too many attempts. Please wait a minute and try again.",
  "auth/network-request-failed": "Connection error. Check your internet and try again.",
};

// Firebase errors carry a code; our own errors (like a missing profile) carry a readable message.
export const authErrorMessage = (err: unknown) => {
  const code = (err as { code?: string }).code;
  if (code) return AUTH_ERRORS[code] ?? "Something went wrong. Please try again.";
  return err instanceof Error ? err.message : "Something went wrong. Please try again.";
};
