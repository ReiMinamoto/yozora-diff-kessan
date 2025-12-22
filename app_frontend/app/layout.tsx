import type { Metadata } from "next";
import "./styles/globals.css";

export const metadata: Metadata = {
  title: "決算短信差分ビューア",
  description: "旧・新PDFの差分要約をローカルで可視化するツール"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="min-h-screen bg-slate-50 font-sans text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
