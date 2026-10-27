import React, { useEffect, useRef, useState } from 'react';
import { sseService } from '../services/sse';
import { SeismicEvent } from '../types';

interface CrackInstance {
  id: number;
  epicenterX: number;
  epicenterY: number;
  paths: string[];       // fisuras principales (zigzag radial)
  branches: string[];    // ramas secundarias
  strokeWidth: number;
  color: string;
  glowColor: string;
  spreadPct: number;     // radio máximo de la grieta (% de la dimensión menor del viewport)
}

const DURATION_MS = 2200;
const MIN_MAG = 2.5; // los microsismos (M<2.5) no rompen la pantalla

/** Escala 0..1 por magnitud: M3.5 -> 0.25, M4.5 -> 0.45, M5.5 -> 0.65, M6.5 -> 0.85, M7+ -> 1 */
function intensity(mag: number): number {
  return Math.min(1, Math.max(0.25, (mag - 2.5) / 5));
}

function buildCrack(id: number, mag: number, tsunami: boolean): CrackInstance {
  const t = intensity(mag);
  const spread = 18 + t * 42;      // 23% .. 60% de la dimensión menor
  const count = Math.round(5 + t * 5); // 6..10 fisuras
  const strokeWidth = 1 + t * 2.2; // px aprox (vector-effect non-scaling-stroke)

  const cx = 30 + Math.random() * 40; // 30-70% ancho
  const cy = 25 + Math.random() * 50; // 25-75% alto

  const paths: string[] = [];
  const branches: string[] = [];

  // Corrección de aspecto: el viewBox es 0 0 100 100 con preserveAspectRatio="none",
  // así que 1 unidad = 1% del ANCHO en X y 1% del ALTO en Y. Sin corrección,
  // en pantallas anchas las grietas se estirarían ~2x horizontalmente.
  // Con (kx, ky) el radio visual queda ≈ igual en píxeles en ambas direcciones,
  // fiel al diseño: spread% de la dimensión menor del viewport.
  const w = typeof window !== 'undefined' ? window.innerWidth : 1280;
  const h = typeof window !== 'undefined' ? window.innerHeight : 720;
  const kx = Math.min(w, h) / Math.max(1, w); // ~0.5 en 1920x1080
  const ky = Math.min(w, h) / Math.max(1, h); // 1.0 en 1920x1080

  for (let i = 0; i < count; i++) {
    const baseAngle = (i / count) * Math.PI * 2 + (Math.random() * 0.5 - 0.25);
    const len = spread * (0.55 + Math.random() * 0.45);
    const segs = 4;
    let d = `M ${cx.toFixed(1)} ${cy.toFixed(1)}`;
    let px = cx;
    let py = cy;
    for (let s = 1; s <= segs; s++) {
      const segLen = (len / segs) * (1 - (s - 1) * 0.08);
      const jitter = baseAngle + (Math.random() * 0.5 - 0.25);
      px += Math.cos(jitter) * segLen * kx;
      py += Math.sin(jitter) * segLen * ky;
      d += ` L ${px.toFixed(1)} ${py.toFixed(1)}`;
      // rama en el segmento medio
      if (s === 2 || s === 3) {
        const bAngle = jitter + (Math.random() > 0.5 ? 0.9 : -0.9);
        const bLen = segLen * (0.35 + Math.random() * 0.3);
        const bx = px + Math.cos(bAngle) * bLen * kx;
        const by = py + Math.sin(bAngle) * bLen * ky;
        branches.push(`M ${px.toFixed(1)} ${py.toFixed(1)} L ${bx.toFixed(1)} ${by.toFixed(1)}`);
      }
    }
    paths.push(d);
  }

  const color = tsunami ? '#ff2d6f' : mag >= 6.0 ? '#ffffff' : '#9be7ff';
  const glowColor = tsunami ? 'rgba(255, 45, 111, 0.55)' : mag >= 6.0 ? 'rgba(255, 255, 255, 0.5)' : 'rgba(155, 231, 255, 0.4)';

  return { id, epicenterX: cx, epicenterY: cy, paths, branches, strokeWidth, color, glowColor, spreadPct: spread };
}

export const ScreenCrackEffect: React.FC = () => {
  const [crack, setCrack] = useState<CrackInstance | null>(null);
  const sessionStartTime = useRef(Date.now());
  const instanceId = useRef(0);
  // Anti-ráfagas: mientras hay una grieta activa se ignora el resto;
  // salvo tsunami o M>=5.5 que la reemplaza de inmediato.
  const activeRef = useRef<{ until: number; mag: number; tsunami: boolean }>({ until: 0, mag: 0, tsunami: false });

  useEffect(() => {
    const unsubscribe = sseService.subscribe((event: SeismicEvent) => {
      const eventTs = new Date(event.updated_time || event.event_time).getTime();
      // Solo eventos genuinamente nuevos de la sesión (mismo criterio del toast)
      if (eventTs < sessionStartTime.current - 10000) return;
      if (event.magnitude < MIN_MAG && !event.tsunami) return;

      const now = Date.now();
      const active = activeRef.current;
      const isBig = event.tsunami || event.magnitude >= 5.5;
      if (now < active.until && !isBig) return;
      if (now < active.until && isBig && !(event.magnitude >= active.mag || event.tsunami)) return;

      activeRef.current = { until: now + DURATION_MS, mag: event.magnitude, tsunami: event.tsunami };
      instanceId.current += 1;

      // limpia el timer previo (p. ej. un reemplazo)
      setCrack(buildCrack(instanceId.current, event.magnitude, event.tsunami));
      const id = instanceId.current;
      setTimeout(() => {
        if (instanceId.current === id) setCrack(null);
      }, DURATION_MS);
    });

    return () => unsubscribe();
  }, []);

  if (!crack) return null;

  return (
    <div
      key={crack.id}
      className="fixed inset-0 z-40 pointer-events-none overflow-hidden"
      aria-hidden="true"
    >
      <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
        {/* halo del epicentro */}
        <circle
          cx={crack.epicenterX}
          cy={crack.epicenterY}
          r={2 + crack.spreadPct * 0.12}
          fill={crack.glowColor}
          className="sw-crack-glow"
        />
        {/* ramas secundarias (más tenues) */}
        {crack.branches.map((d, i) => (
          <path
            key={`b${i}`}
            d={d}
            fill="none"
            stroke={crack.color}
            strokeWidth={crack.strokeWidth * 0.55}
            strokeLinecap="round"
            opacity={0.55}
            vectorEffect="non-scaling-stroke"
            pathLength={1}
            className="sw-crack-line"
            style={{ animationDelay: '60ms' }}
          />
        ))}
        {/* fisuras principales */}
        {crack.paths.map((d, i) => (
          <path
            key={`p${i}`}
            d={d}
            fill="none"
            stroke={crack.color}
            strokeWidth={crack.strokeWidth}
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
            pathLength={1}
            className="sw-crack-line"
            style={{ animationDelay: `${i * 25}ms` }}
          />
        ))}
      </svg>
    </div>
  );
};
