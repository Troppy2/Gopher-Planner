// Mock session. Replace with the real auth client (Google OAuth, @umn.edu only) when it's chosen.
import { create } from "zustand";

const KEY = "gp-session";
const read = () => {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
};
const write = (on: boolean) => {
  try {
    if (on) localStorage.setItem(KEY, "1");
    else localStorage.removeItem(KEY);
  } catch {
    // Storage blocked: the session just won't survive a refresh.
  }
};

interface SessionState {
  signedIn: boolean;
  email: string;
  signIn: () => void;
  signOut: () => void;
}

export const useSession = create<SessionState>((set) => ({
  signedIn: read(),
  email: "inah@umn.edu",
  signIn: () => {
    write(true);
    set({ signedIn: true });
  },
  signOut: () => {
    write(false);
    set({ signedIn: false });
  },
}));
