// frontend/src/app/api/auth/[...nextauth]/route.ts
import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const handler = NextAuth({
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID as string,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
            // NEW: We request specific YouTube permissions from the user
            authorization: {
                params: {
                    prompt: "consent",
                    access_type: "offline",
                    response_type: "code",
                    scope: "openid email profile https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly",
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
                console.error("❌ Error syncing user to backend:", error);
                return true;
            }
        },
        // NEW: We intercept the JWT token to save Google's Access Token
        async jwt({ token, account }) {
            // If the account object exists, it means the user just logged in
            if (account) {
                token.accessToken = account.access_token;
            }
            return token;
        },
        // NEW: We pass the access token to the client session
        async session({ session, token }) {
            // @ts-expect-error - Adding custom property to session
            session.accessToken = token.accessToken;
            return session;
        },
    },
});

export { handler as GET, handler as POST };