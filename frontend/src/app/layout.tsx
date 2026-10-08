import type { Metadata } from "next";
import MotionProvider from "@/components/discovery/MotionProvider";
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
        <MotionProvider>
          <Shell>{children}</Shell>
        </MotionProvider>
      </body>
    </html>
  );
}
