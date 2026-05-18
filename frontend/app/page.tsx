'use client'; // <-- This tells Next.js this entire file runs in the browser context

import dynamic from 'next/dynamic';

// Dynamically import the Map component with SSR completely disabled
const UrbanMap = dynamic(() => import('./components/Map'), {
  ssr: false,
  loading: () => (
    <div className="flex h-screen w-screen flex-col items-center justify-center bg-gray-950 text-white">
      <div className="flex flex-col items-center space-y-4">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent"></div>
        <div className="text-center">
          <p className="text-xl font-semibold tracking-wide text-emerald-400 animate-pulse">
            Initializing Mapbox Engine...
          </p>
          <p className="text-sm text-gray-500 mt-1">Loading urban cooling simulator canvas</p>
        </div>
      </div>
    </div>
  ),
});

export default function Home() {
  return (
    <main className="min-h-screen w-screen overflow-hidden bg-gray-955">
      <UrbanMap />
    </main>
  );
}