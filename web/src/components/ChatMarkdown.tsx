import React from 'react';

/**
 * Renderizador markdown ligero para respuestas del asistente analítico.
 * Soporta: tablas markdown (| a | b |), **negritas**, bloques ```fenced``` y listas "• ".
 * Se usa en el widget flotante y en la página de chat para que comparaciones y
 * tablas certificadas se muestren alineadas (no como texto plano).
 */

const BOLD_RE = /\*\*(.+?)\*\*/g;

const renderInline = (text: string, keyPrefix: string): React.ReactNode[] => {
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  BOLD_RE.lastIndex = 0;
  while ((match = BOLD_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    nodes.push(
      <strong key={`${keyPrefix}-b-${match.index}`} className="font-semibold text-on-surface">
        {match[1]}
      </strong>
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
};

interface TableData {
  header: string[];
  rows: string[][];
}

const parseTableBlock = (lines: string[]): TableData | null => {
  if (lines.length < 2) return null;
  const splitRow = (line: string) =>
    line
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map((c) => c.trim());

  const header = splitRow(lines[0]);
  // La segunda línea es el separador |---|---|
  if (!/^[\s|:-]+$/.test(lines[1])) return null;
  const rows = lines.slice(2).filter((l) => l.trim().startsWith('|')).map(splitRow);
  return { header, rows };
};

export const ChatMarkdown: React.FC<{ text: string }> = ({ text }) => {
  // 1) Divide en bloques ```fenced``` y texto plano.
  const segments: Array<{ type: 'text' | 'code'; content: string }> = [];
  const fenceRe = /```[a-zA-Z]*\n?([\s\S]*?)```/g;
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = fenceRe.exec(text)) !== null) {
    if (match.index > cursor) {
      segments.push({ type: 'text', content: text.slice(cursor, match.index) });
    }
    segments.push({ type: 'code', content: match[1].replace(/\n$/, '') });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) {
    segments.push({ type: 'text', content: text.slice(cursor) });
  }

  return (
    <div className="space-y-2">
      {segments.map((seg, sIdx) => {
        if (seg.type === 'code') {
          return (
            <pre
              key={`code-${sIdx}`}
              className="overflow-x-auto rounded-lg bg-slate-950/80 border border-outline-variant/50 p-3 text-[11px] leading-relaxed font-mono whitespace-pre-wrap"
            >
              {seg.content}
            </pre>
          );
        }
        // 2) En texto plano: agrupa líneas consecutivas en tabla.
        const lines = seg.content.split('\n');
        const blocks: Array<{ kind: 'table'; table: TableData } | { kind: 'line'; line: string }> = [];
        let tableLines: string[] = [];
        for (const line of lines) {
          if (line.trim().startsWith('|')) {
            tableLines.push(line);
          } else {
            if (tableLines.length >= 2) {
              const t = parseTableBlock(tableLines);
              if (t) blocks.push({ kind: 'table', table: t });
              tableLines = [];
            }
            if (tableLines.length === 1) {
              blocks.push({ kind: 'line', line: tableLines[0] });
              tableLines = [];
            }
            blocks.push({ kind: 'line', line });
          }
        }
        if (tableLines.length >= 2) {
          const t = parseTableBlock(tableLines);
          if (t) blocks.push({ kind: 'table', table: t });
        }

        return (
          <div key={`seg-${sIdx}`} className="space-y-1.5">
            {blocks.map((b, bIdx) => {
              if (b.kind === 'table') {
                return (
                  <div
                    key={`tbl-${sIdx}-${bIdx}`}
                    className="overflow-x-auto rounded-lg border border-primary/30 bg-primary-container/10"
                  >
                    <table className="min-w-full text-[11px] text-left">
                      <thead>
                        <tr className="bg-surface-container-high border-b border-outline-variant">
                          {b.table.header.map((h, i) => (
                            <th key={i} className="px-2.5 py-1.5 font-label-md font-semibold text-on-surface whitespace-nowrap">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {b.table.rows.map((r, ri) => (
                          <tr key={ri} className="border-b border-outline-variant/30 last:border-0">
                            {r.map((c, ci) => (
                              <td key={ci} className="px-2.5 py-1.5 text-on-surface whitespace-nowrap">
                                {renderInline(c, `t${sIdx}-${bIdx}-${ri}-${ci}`)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              }
              if (!b.line.trim()) return null;
              return (
                <p key={`l-${sIdx}-${bIdx}`} className="whitespace-pre-wrap leading-relaxed">
                  {renderInline(b.line, `l${sIdx}-${bIdx}`)}
                </p>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};
