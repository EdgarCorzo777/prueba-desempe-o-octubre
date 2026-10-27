import React from 'react';
import { RegionCountItem } from '../types';
import { MapPin } from 'lucide-react';

interface TopRegionsProps {
  regions: RegionCountItem[];
}

export const TopRegions: React.FC<TopRegionsProps> = ({ regions }) => {
  if (!regions || regions.length === 0) {
    return <div className="text-xs text-slate-500 text-center py-4">Sin datos de regiones dominantes.</div>;
  }

  const maxVal = Math.max(...regions.map((r) => r.count), 1);

  return (
    <div className="space-y-3">
      {regions.map((item, idx) => {
        const pct = ((item.count / maxVal) * 100).toFixed(0);

        return (
          <div key={idx} className="p-2.5 rounded-lg bg-sismo-dark/60 border border-slate-800/80 hover:border-slate-700 transition-colors">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="font-semibold text-slate-200 flex items-center gap-1.5 truncate max-w-[200px]">
                <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                {item.region}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-950/50 border border-orange-800/50 text-orange-400 font-mono">
                  M {item.max_magnitude.toFixed(1)}
                </span>
                <span className="text-slate-300 font-mono font-bold text-xs">{item.count}</span>
              </div>
            </div>
            <div className="w-full bg-slate-800/80 rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-violet-500 rounded-full"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
