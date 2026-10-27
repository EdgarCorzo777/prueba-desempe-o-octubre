import React from 'react';
import { TimeSeriesPoint } from '../types';

interface HourlyChartProps {
  data: TimeSeriesPoint[];
}

export const HourlyChart: React.FC<HourlyChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-xs text-slate-500">
        Sin datos de serie temporal en la ventana consultada.
      </div>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const chartHeight = 160;
  const chartWidth = 500;
  const barWidth = Math.max(6, Math.min(24, Math.floor(chartWidth / (data.length * 1.5))));

  return (
    <div className="w-full">
      <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
        <span>Frecuencia horaria (barras cian) y Magnitud pico</span>
        <span className="text-[11px] text-cyan-400 font-mono">Pico: {maxCount} sismos/hora</span>
      </div>
      <div className="relative overflow-x-auto">
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-44 overflow-visible">
          {/* Grid lines */}
          <line x1="0" y1="40" x2={chartWidth} y2="40" stroke="#1e293b" strokeDasharray="3 3" />
          <line x1="0" y1="80" x2={chartWidth} y2="80" stroke="#1e293b" strokeDasharray="3 3" />
          <line x1="0" y1="120" x2={chartWidth} y2="120" stroke="#1e293b" strokeDasharray="3 3" />
          <line x1="0" y1={chartHeight - 20} x2={chartWidth} y2={chartHeight - 20} stroke="#334155" />

          {/* Bars */}
          {data.map((point, idx) => {
            const x = (idx / data.length) * (chartWidth - 40) + 20;
            const barH = (point.count / maxCount) * (chartHeight - 40);
            const y = chartHeight - 20 - barH;
            const hourDisplay = point.hour.split(' ')[1] || point.hour;

            return (
              <g key={idx} className="group cursor-pointer">
                <rect
                  x={x - barWidth / 2}
                  y={y}
                  width={barWidth}
                  height={barH}
                  rx="3"
                  className="fill-cyan-500/60 group-hover:fill-cyan-400 transition-colors"
                />
                {/* Max mag indicator dot */}
                {point.max_magnitude > 0 && (
                  <circle
                    cx={x}
                    cy={Math.max(10, y - (point.max_magnitude * 3))}
                    r="3"
                    className="fill-orange-400 group-hover:r-4 transition-all"
                  />
                )}
                {/* X-axis label for every 3rd or 4th point */}
                {idx % Math.ceil(data.length / 6) === 0 && (
                  <text
                    x={x}
                    y={chartHeight - 4}
                    fontSize="9"
                    fill="#64748b"
                    textAnchor="middle"
                  >
                    {hourDisplay}
                  </text>
                )}
                <title>{`${point.hour}: ${point.count} sismos (M máx: ${point.max_magnitude})`}</title>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
