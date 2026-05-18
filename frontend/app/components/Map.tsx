'use client';

import React, { useEffect, useState } from 'react';
import Map, { NavigationControl, Source, Layer } from 'react-map-gl/mapbox'; 
import 'mapbox-gl/dist/mapbox-gl.css';

interface BuildingProperties {
  id: number;
  baseline_temp: number;
  recommendation: string;
  height: number;
}

type ViewMode = 'baseline' | 'simulated';

export default function UrbanMap() {
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
  
  // App state managers
  const [geoJsonData, setGeoJsonData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedBuilding, setSelectedBuilding] = useState<BuildingProperties | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('baseline');
  const [cursor, setCursor] = useState<string>('auto');

  // Angled view configuration designed to showcase structural 3D relief
  const initialViewState = {
    latitude: 39.1031,
    longitude: -84.5120,
    zoom: 15.2, 
    pitch: 60, 
    bearing: -20,
  };

  useEffect(() => {
    async function fetchBuildings() {
      try {
        const response = await fetch('/api/buildings');
        if (!response.ok) throw new Error('Failed to download database assets.');
        const data = await response.json();
        setGeoJsonData(data);
      } catch (error) {
        console.error('Error hydrating spatial mapping layer:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchBuildings();
  }, []);

  // Raycasting map intersection handler
  const onMapClick = (event: any) => {
    const { features } = event;
    const clickedBuilding = features && features[0];

    if (clickedBuilding) {
      setSelectedBuilding(clickedBuilding.properties as BuildingProperties);
    } else {
      setSelectedBuilding(null);
    }
  };

  const onMouseEnter = () => setCursor('pointer');
  const onMouseLeave = () => setCursor('auto');

  if (!mapboxToken) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-900 text-white">
        <p className="text-xl">Error: Mapbox token missing from .env.local</p>
      </div>
    );
  }

  // Volumetric 3D Extrusion Layer Styling Core Framework
  const building3DLayerStyle: any = {
    id: 'buildings-layer',
    type: 'fill-extrusion', 
    paint: {
      // Dynamic color interpolation executed on the client GPU
      'fill-extrusion-color': [
        'interpolate',
        ['linear'],
        viewMode === 'baseline' 
          ? ['get', 'baseline_temp']
          : [
              '-',
              ['get', 'baseline_temp'],
              [
                'case',
                ['coalesce', ['all', ['in', 'Cool Roof', ['get', 'recommendation']]], ['literal', false]], 15,
                ['coalesce', ['all', ['in', 'Green Roof', ['get', 'recommendation']]], ['literal', false]], 22,
                5
              ]
            ],
        85,  '#2563eb',  // 85°F or lower -> Cool Ambient Blue
        105, '#f59e0b',  // 105°F -> Ambient Amber
        125, '#dc2626'   // 125°F+ -> Scorching Heat Anomaly
      ],
      // Maps the physical extrusion height to the dynamically generated OSM column
      'fill-extrusion-height': ['get', 'height'],
      'fill-extrusion-opacity': 0.85
    }
  };

  const calculateSimulatedTemp = (temp: number, recommendation: string) => {
    if (recommendation.includes('Cool Roof')) return temp - 15;
    if (recommendation.includes('Green Roof')) return temp - 22;
    return temp - 5;
  };

  return (
    <div className="relative w-full h-screen bg-gray-950">
      <Map
        initialViewState={initialViewState}
        mapStyle="mapbox://styles/mapbox/dark-v11" 
        mapboxAccessToken={mapboxToken}
        onClick={onMapClick}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        cursor={cursor}
        interactiveLayerIds={['buildings-layer']}
      >
        <NavigationControl position="top-right" />

        {geoJsonData && (
          <Source id="supabase-buildings" type="geojson" data={geoJsonData}>
            <Layer {...building3DLayerStyle} />
          </Source>
        )}
      </Map>
      
      {/* Simulation Command Center Interface Overlay */}
      <div className="absolute top-4 left-4 z-10 w-96 rounded-xl bg-gray-950/95 p-6 text-white shadow-2xl backdrop-blur-md border border-gray-800 transition-all duration-300">
        <h1 className="text-lg font-bold tracking-tight text-emerald-400">Urban Cooling Simulator 3D</h1>
        
        <div className="mt-4 text-sm text-gray-400 space-y-4">
          {loading ? (
            <p className="animate-pulse text-emerald-500 font-medium">
              Streaming multi-temporal grids from PostGIS matrix...
            </p>
          ) : (
            <div className="space-y-4">
              
              {/* Context Mode Controller */}
              <div className="grid grid-cols-2 gap-2 p-1 bg-gray-900 rounded-lg border border-gray-800">
                <button
                  onClick={() => setViewMode('baseline')}
                  className={`py-2 text-xs font-semibold rounded-md transition-all ${
                    viewMode === 'baseline'
                      ? 'bg-gray-800 text-white shadow'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  Baseline Satellite Heat
                </button>
                <button
                  onClick={() => setViewMode('simulated')}
                  className={`py-2 text-xs font-semibold rounded-md transition-all ${
                    viewMode === 'simulated'
                      ? 'bg-emerald-600 text-white shadow'
                      : 'text-gray-500 hover:text-emerald-500'
                  }`}
                >
                  Simulated Cooling View
                </button>
              </div>

              {/* Dynamic Structural Analysis Module */}
              {selectedBuilding ? (
                <div className="rounded-lg bg-gray-900/60 p-4 border border-gray-800 space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">3D Building Asset</span>
                    <span className="text-xs bg-gray-800 px-2 py-0.5 rounded text-gray-400 font-mono">#{selectedBuilding.id}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="block text-[10px] font-semibold text-gray-500 uppercase">5-Day Satellite Avg</span>
                      <span className="text-xl font-bold text-red-400">{selectedBuilding.baseline_temp.toFixed(1)}°F</span>
                    </div>
                    <div>
                      <span className="block text-[10px] font-semibold text-emerald-500 uppercase">Simulated Target</span>
                      <span className="text-xl font-bold text-emerald-400">
                        {calculateSimulatedTemp(selectedBuilding.baseline_temp, selectedBuilding.recommendation).toFixed(1)}°F
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-gray-800">
                    <span className="block text-xs font-semibold text-gray-400 mb-1">Prescribed Intervention</span>
                    <span className="inline-block text-xs bg-emerald-950/60 border border-emerald-800 text-emerald-400 font-medium px-2.5 py-1 rounded-md">
                      {selectedBuilding.recommendation}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-gray-800 p-5 text-center text-gray-500">
                  <p className="text-xs">Hold right-click + drag to pan/tilt camera. Click any architectural model to audit thermal signatures.</p>
                </div>
              )}

              {/* Spatial Gradient Index */}
              <div className="pt-2 border-t border-gray-900">
                <span className="block text-[11px] uppercase font-semibold text-gray-500 mb-1.5">Calibrated LST Gradient</span>
                <div className="h-2 w-full rounded bg-gradient-to-r from-blue-600 via-amber-500 to-red-600" />
                <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                  <span>85°F (Ambient)</span>
                  <span>125°F+ (Thermal Anomaly)</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}