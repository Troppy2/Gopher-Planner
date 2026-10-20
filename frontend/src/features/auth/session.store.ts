import { create } from "zustand";
import { getCurrentSession, logoutFromServer } from "./google";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  picture: string;
}

interface SessionState {
  signedIn: boolean;
  initialized: boolean;
  email: string;
  user: AuthUser | null;

  signIn: (user: AuthUser) => void;
  restoreSession: () => Promise<void>;
  signOut: () => Promise<void>;
}

export const useSession = create<SessionState>((set) => ({
  signedIn: false,
  initialized: false,
  email: "",
  user: null,

  signIn: (user) => {
    set({
      signedIn: true,
      initialized: true,
      email: user.email,
      user,
    });
  },

  restoreSession: async () => {
    try {
      const user = await getCurrentSession();

      set({
        signedIn: true,
        initialized: true,
        email: user.email,
        user,
      });
    } catch {
      set({
        signedIn: false,
        initialized: true,
        email: "",
        user: null,
      });
    }
  },

  signOut: async () => {
    try {
      await logoutFromServer();
    } finally {
      set({
        signedIn: false,
        initialized: true,
        email: "",
        user: null,
      });
    }
  },
}));
