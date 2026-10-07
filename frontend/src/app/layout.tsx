import type { Metadata } from "next";
import Shell from "@/components/Shell";
import "./globals.css";
import "./theme.css";
import "./discovery.css";
export const metadata: Metadata = {
  title: "Knowledge Product Manager",
  description:
    "Discover governed knowledge products, data assets and evidence.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
