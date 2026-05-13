import './globals.css';

export const metadata = {
  title: 'Agentic Content System',
  description: 'Multi-agent AI content generation pipeline',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
