"use client";
import { MotionConfig, LayoutGroup } from "framer-motion";
export default function MotionProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <MotionConfig
      reducedMotion="user"
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
    >
      <LayoutGroup>{children}</LayoutGroup>
    </MotionConfig>
  );
}
