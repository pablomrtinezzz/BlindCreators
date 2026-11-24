/**
 * Server-side proxy to the FastAPI backend.
 *
 * The browser only ever calls /api/backend/*. This handler reads the NextAuth session cookie,
 * signs a 2-minute JWT for the backend and, for sync requests only, attaches the Google access
 * token. Google tokens never reach client-side JavaScript.
 */
import { SignJWT } from "jose";
import { getToken } from "next-auth/jwt";
import { type NextRequest, NextResponse } from "next/server";
import { refreshGoogleToken } from "@/lib/auth";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const SEGMENT = /^[A-Za-z0-9_.-]+$/;

async function signBackendToken(claims: { email: string; name?: string | null; picture?: string | null; verified: boolean; sub?: string }) {
  const secret = process.env.BACKEND_JWT_SECRET;
  if (!secret || secret.length < 32) throw new Error("BACKEND_JWT_SECRET is missing or too short");
  return new SignJWT({
    email: claims.email,
    email_verified: claims.verified,
    name: claims.name ?? undefined,
    picture: claims.picture ?? undefined,
  })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setSubject(claims.sub ?? claims.email)
    .setIssuer("blindcreators-web")
    .setAudience("blindcreators-api")
    .setIssuedAt()
    .setExpirationTime("2m")
    .sign(new TextEncoder().encode(secret));
}

async function handler(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  if (!path.length || !path.every((p) => SEGMENT.test(p))) {
    return NextResponse.json({ detail: "Invalid path" }, { status: 400 });
  }

  let token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  if (!token?.email) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  const headers = new Headers({ Accept: "application/json" });
  try {
    headers.set(
      "Authorization",
      `Bearer ${await signBackendToken({
        email: token.email,
        name: token.name,
        picture: token.picture,
        verified: token.emailVerified === true,
        sub: token.sub,
      })}`,
    );
  } catch (err) {
    console.error("[proxy]", err instanceof Error ? err.message : err);
    return NextResponse.json({ detail: "Server misconfigured" }, { status: 500 });
  }

  const isSync = req.method === "POST" && path.length === 1 && path[0] === "sync";
  if (isSync) {
    if (!token.googleExpiresAt || Date.now() > token.googleExpiresAt - 10 * 60_000) {
      token = await refreshGoogleToken(token);
    }
    if (token.error || !token.googleAccessToken) {
      return NextResponse.json({ detail: "Your Google session expired. Sign out and sign in again." }, { status: 401 });
    }
    headers.set("X-Google-Access-Token", token.googleAccessToken);
  }

  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);

  const url = `${BACKEND_URL}/api/v1/${path.join("/")}${req.nextUrl.search}`;
  try {
    const res = await fetch(url, {
      method: req.method,
      headers,
      body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    });
    if (res.status === 204) return new NextResponse(null, { status: 204 });
    return new NextResponse(res.body, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "The analytics server is not reachable. Is the backend running?" }, { status: 502 });
  }
}

export { handler as GET, handler as POST, handler as DELETE };
