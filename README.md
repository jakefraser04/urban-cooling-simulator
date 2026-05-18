## Current Status: 3D Simulator Deployment Block

- **Local State:** Complete and verified. The data pipelines (`harvest_landsat.py`, `harvest_skyline.py`, `update_temperatures.py`) have successfully compiled multi-day satellite heat maps and true structural OpenStreetMap heights into the Supabase database. Local development server runs the hardware-accelerated 3D Mapbox camera perfectly.
- **Vercel Build Status:** Deployments are green/successful, meaning the Next.js API routes and React nodes are compiling perfectly from the `/frontend` subfolder.
- **The Bug:** The production domain (`urban-cooling-simulator.vercel.app`) is throwing a persistent `404: NOT_FOUND`, indicating Vercel's edge router isn't mapping the base path `/` directly to the compiled Next.js entry page.