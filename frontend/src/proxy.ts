import { getToken } from "next-auth/jwt";
import { type NextRequest, NextResponse } from "next/server";

/** Redirects signed-out visitors to /login. API routes enforce auth themselves. */
export async function proxy(req: NextRequest) {
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  if (token) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  if (req.nextUrl.pathname !== "/") url.searchParams.set("callbackUrl", req.nextUrl.pathname + req.nextUrl.search);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!api|login|_next/static|_next/image|icon.svg|favicon.ico).*)"],
};
