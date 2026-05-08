import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Amplify } from "aws-amplify";

import App from "./App";
import { CognitoProvider } from "./auth/CognitoProvider";
import "./styles/globals.css";

const userPoolId = import.meta.env.VITE_USER_POOL_ID as string | undefined;
const userPoolClientId = import.meta.env.VITE_USER_POOL_CLIENT_ID as string | undefined;
const region = (import.meta.env.VITE_REGION as string | undefined) ?? "eu-central-1";

// eslint-disable-next-line no-console
console.log("[Konsultacije] env @ boot", {
  VITE_REGION: region,
  VITE_USER_POOL_ID: userPoolId,
  VITE_USER_POOL_CLIENT_ID: userPoolClientId,
  VITE_API_URL: import.meta.env.VITE_API_URL,
  MODE: import.meta.env.MODE,
});

if (!userPoolId || !userPoolClientId) {
  // eslint-disable-next-line no-console
  console.error(
    "[Konsultacije] VITE_USER_POOL_ID i/ili VITE_USER_POOL_CLIENT_ID nisu postavljeni.\n" +
      "Proveri frontend/.env i restartuj `npm run dev` (Vite čita env samo pri startu).",
  );
}

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: userPoolId ?? "",
      userPoolClientId: userPoolClientId ?? "",
    },
  },
});

// eslint-disable-next-line no-console
console.log("[Konsultacije] Amplify.getConfig() po konfiguraciji:", Amplify.getConfig());

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <CognitoProvider>
          <App />
        </CognitoProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
