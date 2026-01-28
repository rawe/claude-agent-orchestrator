import { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { Info, X } from 'lucide-react';

interface InfoPopoverProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function InfoPopover({ title, children, className = '' }: InfoPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{ top: number; left: number }>({ top: 0, left: 0 });

  // Calculate position before paint using useLayoutEffect
  useLayoutEffect(() => {
    if (!isOpen || !triggerRef.current) return;

    const updatePosition = () => {
      if (!triggerRef.current) return;

      const trigger = triggerRef.current.getBoundingClientRect();
      const popoverWidth = 320; // w-80 = 20rem = 320px
      const popoverHeight = popoverRef.current?.offsetHeight || 200;
      const gap = 4;

      const viewport = {
        width: window.innerWidth,
        height: window.innerHeight,
      };

      // Position below trigger, centered on trigger
      let top = trigger.bottom + gap;
      let left = trigger.left + (trigger.width / 2) - (popoverWidth / 2);

      // Adjust if popover would go off right edge
      if (left + popoverWidth > viewport.width - 16) {
        left = viewport.width - popoverWidth - 16;
      }

      // Adjust if popover would go off left edge
      if (left < 16) {
        left = 16;
      }

      // Adjust if popover would go off bottom - position above instead
      if (top + popoverHeight > viewport.height - 16) {
        top = trigger.top - popoverHeight - gap;
      }

      setPosition({ top, left });
    };

    updatePosition();

    // Recalculate after popover renders to get accurate height
    requestAnimationFrame(updatePosition);
  }, [isOpen]);

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  const popoverContent = isOpen ? (
    <div
      ref={popoverRef}
      className="fixed z-[100] w-80 max-w-[calc(100vw-32px)] bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden"
      style={{ top: position.top, left: position.left }}
    >
      {title && (
        <div className="bg-gradient-to-r from-primary-50 to-gray-50 px-4 py-2 border-b border-gray-100 flex items-center justify-between">
          <span className="text-sm font-medium text-gray-900">{title}</span>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      <div className="px-4 py-3 text-sm text-gray-600 space-y-2">
        {children}
      </div>
    </div>
  ) : null;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600 transition-colors ${className}`}
        aria-label="More information"
      >
        <Info className="w-4 h-4" />
      </button>
      {popoverContent && createPortal(popoverContent, document.body)}
    </>
  );
}
