/**
 * Resizable Panels Component
 * Allows dragging divider to resize panels
 */

import { useRef, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { GripVertical } from 'lucide-react';

interface ResizablePanelsProps {
  left: ReactNode;
  right: ReactNode;
  defaultLeftWidth?: number; // percentage (0-100)
  minLeftWidth?: number; // percentage
  minRightWidth?: number; // percentage
}

export function ResizablePanels({
  left,
  right,
  defaultLeftWidth = 50,
  minLeftWidth = 20,
  minRightWidth = 20,
}: ResizablePanelsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;

      const container = containerRef.current;
      const containerRect = container.getBoundingClientRect();
      const containerWidth = containerRect.width;
      const mouseX = e.clientX - containerRect.left;

      // Calculate new percentage
      let newLeftWidth = (mouseX / containerWidth) * 100;

      // Apply constraints
      newLeftWidth = Math.max(minLeftWidth, Math.min(100 - minRightWidth, newLeftWidth));

      setLeftWidth(newLeftWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, minLeftWidth, minRightWidth]);

  const handleMouseDown = () => {
    setIsDragging(true);
  };

  return (
    <div ref={containerRef} className="flex h-full w-full overflow-hidden">
      {/* Left panel */}
      <div style={{ width: `${leftWidth}%` }} className="overflow-hidden">
        {left}
      </div>

      {/* Divider */}
      <div
        className="w-1 bg-white/5 hover:bg-purple-500/50 cursor-col-resize transition-colors relative group"
        onMouseDown={handleMouseDown}
      >
        <div className="absolute inset-y-0 -left-1 -right-1 flex items-center justify-center">
          <GripVertical className="w-4 h-4 text-zinc-600 group-hover:text-purple-400 transition-colors" />
        </div>
      </div>

      {/* Right panel */}
      <div style={{ width: `${100 - leftWidth}%` }} className="overflow-hidden">
        {right}
      </div>
    </div>
  );
}
