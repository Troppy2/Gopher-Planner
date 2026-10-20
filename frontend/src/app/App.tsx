import { useEffect } from "react";
import { RouterProvider } from "react-router";
import { Providers } from "./providers";
import { router } from "./router";
import { useSession } from "@/features/auth/session.store";

function SessionInitializer() {
  const restoreSession = useSession((state) => state.restoreSession);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  return null;
}

export default function App() {
  return (
    <Providers>
      <SessionInitializer />
      <RouterProvider router={router} />
    </Providers>
  );
}
