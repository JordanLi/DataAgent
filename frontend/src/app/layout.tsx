import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataAgent — 数据智能体",
  description: "Natural language data query and analysis agent",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
