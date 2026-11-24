import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    error?: "RefreshAccessTokenError";
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    googleAccessToken?: string;
    googleRefreshToken?: string;
    googleExpiresAt?: number;
    emailVerified?: boolean;
    error?: "RefreshAccessTokenError";
  }
}
