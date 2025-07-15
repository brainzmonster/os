// Footer component for the brainzOS web UI
// Displays static footer text with dynamic current year

export default function Footer() {
  return (
    <footer className="w-full border-t p-4 text-center text-sm text-gray-500">
      {/* Dynamic year rendering and static project tagline */}
      brainzOS © {new Date().getFullYear()} • Built for crypto & tech
    </footer>
  );
}
