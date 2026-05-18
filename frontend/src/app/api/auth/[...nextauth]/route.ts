import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

async function refreshAccessToken(token: any) {
    try {
        const url = "https://oauth2.googleapis.com/token";
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
                client_id: process.env.GOOGLE_CLIENT_ID!,
                client_secret: process.env.GOOGLE_CLIENT_SECRET!,
                grant_type: "refresh_token",
                refresh_token: token.refreshToken,
            }),
        });

        const refreshed = await res.json();
        if (!res.ok) throw refreshed;

        return {
            ...token,
            accessToken: refreshed.access_token,
            // Google only returns a new refresh_token if the old one is revoked
            refreshToken: refreshed.refresh_token ?? token.refreshToken,
            accessTokenExpires: Date.now() + refreshed.expires_in * 1000,
        };
    } catch (error) {
        console.error("Token refresh error:", error);
        return { ...token, error: "RefreshAccessTokenError" };
    }
}

const handler = NextAuth({
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID as string,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
            authorization: {
                params: {
                    prompt: "consent",
                    access_type: "offline",
                    response_type: "code",
                    scope: "openid email profile https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.force-ssl https://www.googleapis.com/auth/yt-analytics.readonly",
                },
            },
        }),
    ],
    secret: process.env.NEXTAUTH_SECRET,

    callbacks: {
        async signIn({ user }) {
            try {
                await fetch("http://127.0.0.1:8000/api/v1/users/sync", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        email: user.email,
                        name: user.name,
                        image: user.image,
                    }),
                });
                return true;
            } catch (error) {
                console.error("Error syncing user:", error);
                return true;
            }
        },

        async jwt({ token, account }) {
            // First login: save token + expiry + refresh_token
            if (account) {
                return {
                    ...token,
                    accessToken: account.access_token,
                    refreshToken: account.refresh_token,
                    // Google tokens expire in 3600s; subtract 60s buffer
                    accessTokenExpires: Date.now() + (account.expires_in as number) * 1000 - 60_000,
                };
            }

            // Token still valid — return as-is
            if (Date.now() < (token.accessTokenExpires as number)) {
                return token;
            }

            // Token expired — refresh it
            return refreshAccessToken(token);
        },

        async session({ session, token }) {
            // @ts-expect-error - custom properties
            session.accessToken = token.accessToken;
            // @ts-expect-error
            session.error = token.error;
            return session;
        },
    },
});

export { handler as GET, handler as POST };
