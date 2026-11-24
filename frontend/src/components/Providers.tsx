"use client";

import { SessionProvider } from "next-auth/react";
import { SWRConfig } from "swr";
import { ApiError, fetcher } from "@/lib/api";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    // Refetching the session every 5 min lets NextAuth refresh and persist the Google token.
    <SessionProvider refetchInterval={5 * 60}>
      <SWRConfig
        value={{
          fetcher,
          revalidateOnFocus: false,
          shouldRetryOnError: (err) => !(err instanceof ApiError && err.status < 500),
          errorRetryCount: 2,
        }}
      >
        {children}
      </SWRConfig>
    </SessionProvider>
  );
}
