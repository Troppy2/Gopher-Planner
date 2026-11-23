import { setupServer } from "msw/node";

/** MSW server; each test registers handlers that mirror the backend contracts. */
export const server = setupServer();
export const api = (path: string) => `http://localhost:3000/api/v1${path}`;
