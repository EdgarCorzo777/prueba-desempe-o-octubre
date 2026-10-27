import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { SeismicEvent } from '../types';

interface EarthquakeMapProps {
  events: SeismicEvent[];
  selectedEvent?: SeismicEvent | null;
  onSelectEvent?: (event: SeismicEvent) => void;
}

export const EarthquakeMap: React.FC<EarthquakeMapProps> = ({
  events,
  selectedEvent,
  onSelectEvent
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      // Initialize map with CartoDB Dark Matter tiles for a futuristic observatory aesthetic
      const map = L.map(mapContainerRef.current, {
        center: [20.0, 0.0],
        zoom: 2,
        minZoom: 1.5,
        maxZoom: 12,
        worldCopyJump: true
      });

      L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        {
          attribution: '&copy; <a href="https://www.esri.com/" target="_blank" rel="noopener noreferrer">Esri</a> &copy; USGS',
          maxZoom: 16
        }
      ).addTo(map);

      layerGroupRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current || !layerGroupRef.current) return;

    layerGroupRef.current.clearLayers();

    const getColor = (mag: number, tsunami: boolean) => {
      if (tsunami) return '#ff0055';
      if (mag >= 7.0) return '#ef4444';
      if (mag >= 6.0) return '#f97316';
      if (mag >= 4.0) return '#00f0ff';
      return '#10b981';
    };

    events.forEach((ev) => {
      if (typeof ev.latitude !== 'number' || typeof ev.longitude !== 'number') return;

      const color = getColor(ev.magnitude, ev.tsunami);
      const radius = Math.max(4, Math.min(ev.magnitude * 2.8, 22));

      const circle = L.circleMarker([ev.latitude, ev.longitude], {
        radius,
        fillColor: color,
        color: '#ffffff',
        weight: 1,
        opacity: 0.9,
        fillOpacity: 0.65
      });

      const popupHtml = `
        <div style="font-family: inherit; font-size: 12px; color: #1e293b; min-width: 180px;">
          <div style="font-weight: 800; font-size: 14px; color: ${color}; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 6px;">
            M ${ev.magnitude.toFixed(1)} &bull; ${ev.severity_level}
          </div>
          <div><strong>Lugar:</strong> ${ev.place}</div>
          <div><strong>Profundidad:</strong> ${ev.depth_km.toFixed(1)} km</div>
          <div><strong>Fecha:</strong> ${new Date(ev.event_time).toLocaleString()}</div>
          ${ev.tsunami ? '<div style="color: #ef4444; font-weight: bold; margin-top: 4px; display: flex; align-items: center; gap: 4px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg> ALERTA DE TSUNAMI</div>' : ''}
          ${ev.url ? `<div style="margin-top: 6px;"><a href="${ev.url}" target="_blank" style="color: #0284c7; text-decoration: underline;">Ver ficha USGS</a></div>` : ''}
        </div>
      `;

      circle.bindPopup(popupHtml);
      circle.on('click', () => {
        if (onSelectEvent) onSelectEvent(ev);
      });

      circle.addTo(layerGroupRef.current!);
    });

    if (mapInstanceRef.current) {
      setTimeout(() => mapInstanceRef.current?.invalidateSize(), 100);
    }

    if (selectedEvent && mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([selectedEvent.latitude, selectedEvent.longitude], 6, {
        duration: 1.2
      });
    }
  }, [events, selectedEvent, onSelectEvent]);

  return (
    <div className="relative isolate z-0 w-full h-full min-h-[460px] rounded-xl overflow-hidden border border-slate-800 bg-[#0b0f19] shadow-2xl">
      <div ref={mapContainerRef} className="w-full h-full bg-[#0b0f19]" />
      {/* Map Legend Overlay - Placed at Top-Right so it is always 100% visible immediately without scrolling */}
      <div className="absolute top-3 right-3 z-[1000] bg-slate-900/95 backdrop-blur-md border border-slate-600 rounded-xl p-3 text-[11px] text-slate-200 flex flex-col gap-2 shadow-2xl">
        <span className="font-bold text-slate-100 border-b border-slate-700 pb-1 mb-0.5 tracking-wider uppercase text-[10px] text-cyan-300">
          Convención de Severidad
        </span>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-500 inline-block"></span> M ≥ 7.0 Crítico</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-orange-500 inline-block"></span> M 6.0 - 6.9 Fuerte</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-cyan-400 inline-block"></span> M 4.0 - 5.9 Moderado</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span> M {'<'} 4.0 Menor</div>
        <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-pink-500 ring-2 ring-red-400 animate-pulse inline-block"></span> Alerta Tsunami</div>
      </div>
    </div>
  );
};
