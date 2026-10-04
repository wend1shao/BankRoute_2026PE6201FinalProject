import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") || requestHeaders.get("host") || "localhost";
  const protocol = requestHeaders.get("x-forwarded-proto") || (host.includes("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;
  return {
    title: "BankRoute | Agent Routing Decision Support",
    description: "A guarded AI routing prototype for first-line banking service agents.",
    openGraph: {
      title: "BankRoute | Agent Routing Decision Support",
      description: "Recommend a specialist queue, show confidence, and escalate uncertain or unsafe enquiries for human review.",
      images: [`${origin}/og.png`],
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: "BankRoute | Agent Routing Decision Support",
      description: "A guarded AI routing prototype for first-line banking service agents.",
      images: [`${origin}/og.png`],
    },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
