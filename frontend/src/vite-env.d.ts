/// <reference types="google.accounts" />

export {};

declare global {
  interface Window {
    google?: typeof google;
  }
}
