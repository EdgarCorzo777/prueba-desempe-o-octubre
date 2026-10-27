import React from 'react';
import { MagnitudeDistItem } from '../types';

interface MagnitudeDistributionProps {
  data: MagnitudeDistItem[];
}

interface SeverityTier {
  key: string;
  label: string;
  color: string;
  textColor: string;
}

const ORDERED_TIERS: SeverityTier[] = [
  { key: 'CRITICAL', label: 'Crítico (M ≥ 7.0)', color: 'bg-red-500', textColor: 'text-red-400' },
  { key: 'HIGH', label: 'Fuerte (M 6.0 - 6.9)', color: 'bg-orange-500', textColor: 'text-orange-400' },
  { key: 'MODERATE', label: 'Moderado (M 4.0 - 5.9)', color: 'bg-cyan-400', textColor: 'text-cyan-400' },
  { key: 'LOW', label: 'Menor (M < 4.0)', color: 'bg-emerald-500', textColor: 'text-emerald-400' },
];

export const MagnitudeDistribution: React.FC<MagnitudeDistributionProps> = ({ data }) => {
  const dataMap = new Map<string, number>();
  (data || []).forEach((d) => {
    dataMap.set(d.severity.toUpperCase(), d.count);
  });

  const total = Array.from(dataMap.values()).reduce((acc, curr) => acc + curr, 0);

  return (
    <div className="space-y-3">
      {ORDERED_TIERS.map((tier) => {
        const count = dataMap.get(tier.key) || 0;
        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';

        return (
          <div key={tier.key} className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className={`font-medium ${tier.textColor}`}>{tier.label}</span>
              <span className="text-slate-400 font-mono text-[11px]">
                {count} ({pct}%)
              </span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full ${tier.color} rounded-full transition-all duration-500`}
                style={{ width: `${Math.max(count > 0 ? 2 : 0, parseFloat(pct))}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
