// Simple React component to display information about brainzOS
export default function AboutPage() {
  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Page title */}
      <h1 className="text-2xl font-bold mb-4">About brainzOS/h1>

      {/* Description of what brainzOS is and who it's for */}
      <p className="text-gray-700">
        brainzOS is an experimental AI operating system designed to train, adapt, and respond to technical prompts in the crypto, blockchain, and software ecosystems. Built for developers, researchers, and builders.
      </p>
    </div>
  );
}
