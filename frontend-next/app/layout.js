import './globals.css';

export const metadata = {
  title: 'Job Search AI Agent',
  description: 'AI-powered job search and interview prep assistant',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
