import "./globals.css";

export const metadata = {
  title: "Python Code Tutor",
  description: "AI-assisted Python code feedback for beginners",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}

