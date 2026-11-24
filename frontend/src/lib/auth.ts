import type { NextAuthOptions } from "next-auth";
import type { JWT } from "next-auth/jwt";
import GoogleProvider from "next-auth/providers/google";

/** Read-only scopes: the app never writes to the channel. */
export const YOUTUBE_SCOPES = [
  "https://www.googleapis.com/auth/youtube.readonly",
  "https://www.googleapis.com/auth/yt-analytics.readonly",
];

/** True when Google granted every YouTube scope (users can untick them on the consent screen). */
export const hasYouTubeScopes = (granted?: string) =>
  YOUTUBE_SCOPES.every((s) => (granted ?? "").split(" ").includes(s));

const SCOPES = [
  "openid",
  "email",
  "profile",
  "https://www.googleapis.com/auth/youtube.readonly",
  "https://www.googleapis.com/auth/yt-analytics.readonly",
].join(" ");

export async function refreshGoogleToken(token: JWT): Promise<JWT> {
  if (!token.googleRefreshToken) return { ...token, error: "RefreshAccessTokenError" };
  try {
    const res = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: process.env.GOOGLE_CLIENT_ID ?? "",
        client_secret: process.env.GOOGLE_CLIENT_SECRET ?? "",
        grant_type: "refresh_token",
        refresh_token: token.googleRefreshToken,
      }),
    });
    const data = (await res.json()) as { access_token?: string; expires_in?: number; refresh_token?: string };
    if (!res.ok || !data.access_token) throw new Error(`refresh failed (${res.status})`);
    return {
      ...token,
      googleAccessToken: data.access_token,
      googleExpiresAt: Date.now() + (data.expires_in ?? 3600) * 1000,
      googleRefreshToken: data.refresh_token ?? token.googleRefreshToken,
      error: undefined,
    };
  } catch (err) {
    console.error("[auth] Google token refresh failed:", err instanceof Error ? err.message : err);
    return { ...token, error: "RefreshAccessTokenError" };
  }
}

export const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
      authorization: {
        params: { prompt: "consent", access_type: "offline", response_type: "code", scope: SCOPES },
      },
    }),
  ],
  callbacks: {
    async signIn({ profile }) {
      // Only accept Google accounts with a verified email.
      return (profile as { email_verified?: boolean } | undefined)?.email_verified === true;
    },
    async jwt({ token, account, profile }) {
      if (account) {
        return {
          ...token,
          googleAccessToken: account.access_token,
          googleRefreshToken: account.refresh_token,
          googleExpiresAt: (account.expires_at ?? Math.floor(Date.now() / 1000) + 3600) * 1000,
          emailVerified: (profile as { email_verified?: boolean } | undefined)?.email_verified === true,
          grantedScopes: account.scope,
          error: undefined,
        };
      }
      if (token.googleExpiresAt && Date.now() < token.googleExpiresAt - 5 * 60_000) return token;
      return refreshGoogleToken(token);
    },
    async session({ session, token }) {
      // Google tokens stay server-side, in the encrypted JWT cookie. Never expose them here.
      session.error = token.error;
      session.missingYouTubeAccess = !hasYouTubeScopes(token.grantedScopes);
      return session;
    },
  },
};
