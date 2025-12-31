/**
 * CSV Preview Component - Web3 Dark Theme
 * Displays CSV data as a formatted table
 */

import { useState, useEffect } from 'react';
import { Download, Search } from 'lucide-react';

interface CSVPreviewProps {
  content: string;
  filePath?: string;
}

export function CSVPreview({ content, filePath }: CSVPreviewProps) {
  const [rows, setRows] = useState<string[][]>([]);
  const [headers, setHeaders] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [delimiter, setDelimiter] = useState(',');

  useEffect(() => {
    parseCSV(content, delimiter);
  }, [content, delimiter]);

  const parseCSV = (csv: string, delim: string) => {
    const lines = csv.trim().split('\n');
    if (lines.length === 0) return;

    // Parse headers
    const headerRow = lines[0].split(delim).map(h => h.trim().replace(/^"|"$/g, ''));
    setHeaders(headerRow);

    // Parse data rows
    const dataRows = lines.slice(1).map(line => {
      return line.split(delim).map(cell => cell.trim().replace(/^"|"$/g, ''));
    });
    setRows(dataRows);
  };

  const filteredRows = rows.filter(row =>
    row.some(cell =>
      cell.toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  const handleExportCSV = () => {
    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filePath?.split('/').pop() || 'export.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-purple-900/10 to-slate-900">
      {/* Toolbar */}
      <div className="glass-card border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="px-3 py-1 bg-green-500/10 text-green-400 text-xs font-medium rounded-lg border border-green-500/20">
            CSV • {rows.length} rows × {headers.length} columns
          </div>

          {/* Delimiter selector */}
          <select
            value={delimiter}
            onChange={(e) => setDelimiter(e.target.value)}
            className="px-3 py-1 bg-white/5 text-zinc-300 text-xs rounded-lg border border-white/10 focus:outline-none focus:border-purple-500/50"
          >
            <option value=",">Comma (,)</option>
            <option value=";">Semicolon (;)</option>
            <option value="\t">Tab</option>
            <option value="|">Pipe (|)</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search..."
              className="pl-10 pr-4 py-2 bg-white/5 text-zinc-300 text-sm rounded-lg border border-white/10 focus:outline-none focus:border-purple-500/50 w-48"
            />
          </div>

          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-3 py-2 hover:bg-white/5 rounded-lg transition-colors group"
          >
            <Download className="w-4 h-4 text-zinc-400 group-hover:text-green-400" />
            <span className="text-xs text-zinc-400 group-hover:text-green-400">Export</span>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 glass-card border-b border-white/10">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-purple-400 border-r border-white/5 bg-purple-500/5">
                #
              </th>
              {headers.map((header, i) => (
                <th
                  key={i}
                  className="px-4 py-3 text-left text-xs font-semibold text-purple-400 border-r border-white/5"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className="border-b border-white/5 hover:bg-white/5 transition-colors"
              >
                <td className="px-4 py-3 text-zinc-500 border-r border-white/5 font-mono text-xs">
                  {rowIndex + 1}
                </td>
                {row.map((cell, cellIndex) => (
                  <td
                    key={cellIndex}
                    className="px-4 py-3 text-zinc-300 border-r border-white/5"
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {filteredRows.length === 0 && (
          <div className="p-12 text-center">
            <p className="text-zinc-500">
              {searchTerm ? 'No matching rows found' : 'No data to display'}
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      {searchTerm && (
        <div className="glass-card border-t border-white/5 px-4 py-2">
          <p className="text-xs text-zinc-500">
            Showing {filteredRows.length} of {rows.length} rows
          </p>
        </div>
      )}
    </div>
  );
}
