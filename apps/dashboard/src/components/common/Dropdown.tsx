import { useState, useRef, useEffect, ReactNode, useMemo, useCallback } from 'react';
import { ChevronDown, Check, Search, RotateCw, Info } from 'lucide-react';

export interface DropdownOption<T = string> {
  value: T;
  label: string;
  description?: string;
  icon?: ReactNode;
}

// Individual dropdown item with hover description popover
function DropdownItem<T>({
  option,
  isSelected,
  onSelect,
  menuAlign,
}: {
  option: DropdownOption<T>;
  isSelected: boolean;
  onSelect: () => void;
  menuAlign: 'left' | 'right';
}) {
  const [showPopover, setShowPopover] = useState(false);
  const [popoverPosition, setPopoverPosition] = useState<{ top: number; left: number } | null>(null);
  // Track popover side for potential future arrow/pointer indicator
  const [_popoverSide, setPopoverSide] = useState<'left' | 'right'>('left');
  const itemRef = useRef<HTMLButtonElement>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const calculatePopoverPosition = useCallback(() => {
    if (!itemRef.current) return;
    const rect = itemRef.current.getBoundingClientRect();
    const popoverWidth = 280;
    const spaceRight = window.innerWidth - rect.right;
    const spaceLeft = rect.left;

    // Determine which side has more space
    const showOnLeft = menuAlign === 'right' ? spaceLeft > popoverWidth : spaceRight < popoverWidth;
    setPopoverSide(showOnLeft ? 'left' : 'right');

    // Calculate position
    const top = rect.top;
    const left = showOnLeft ? rect.left - popoverWidth - 8 : rect.right + 8;

    setPopoverPosition({ top, left });
  }, [menuAlign]);

  const handleMouseEnter = () => {
    if (!option.description) return;
    calculatePopoverPosition();
    hoverTimeoutRef.current = setTimeout(() => setShowPopover(true), 200);
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    setShowPopover(false);
  };

  return (
    <>
      <button
        ref={itemRef}
        type="button"
        onClick={onSelect}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className={`
          w-full flex items-center gap-3 px-3 py-2 text-left
          transition-colors
          ${isSelected
            ? 'bg-primary-50'
            : 'hover:bg-gray-50'
          }
        `}
      >
        {/* Check mark or empty space for alignment */}
        <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
          {isSelected && <Check className="w-4 h-4 text-primary-600" />}
        </span>

        {/* Label */}
        <span className={`flex-1 text-sm font-medium truncate ${isSelected ? 'text-primary-700' : 'text-gray-900'}`}>
          {option.label}
        </span>

        {/* Info icon hint for description */}
        {option.description && (
          <Info className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
        )}
      </button>

      {/* Description Popover - rendered with fixed positioning to escape overflow */}
      {showPopover && option.description && popoverPosition && (
        <div
          className="fixed z-[9999] w-[280px] pointer-events-none"
          style={{
            top: popoverPosition.top,
            left: popoverPosition.left,
          }}
        >
          <div className="bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className="px-4 py-2.5 bg-gradient-to-r from-primary-50 to-gray-50 border-b border-gray-100">
              <div className="text-sm font-semibold text-gray-900">{option.label}</div>
            </div>
            {/* Description */}
            <div className="px-4 py-3">
              <p className="text-sm text-gray-600 leading-relaxed">
                {option.description}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

interface DropdownProps<T = string> {
  options: DropdownOption<T>[];
  value: T;
  onChange: (value: T) => void;
  placeholder?: string;
  icon?: ReactNode;
  disabled?: boolean;
  className?: string;
  menuAlign?: 'left' | 'right';
  size?: 'sm' | 'md';
  searchable?: boolean;
  searchPlaceholder?: string;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export function Dropdown<T = string>({
  options,
  value,
  onChange,
  placeholder = 'Select...',
  icon,
  disabled = false,
  className = '',
  menuAlign = 'left',
  size = 'md',
  searchable = false,
  searchPlaceholder = 'Search...',
  onRefresh,
  isRefreshing = false,
}: DropdownProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Close on escape
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen]);

  // Focus search input when opened
  useEffect(() => {
    if (isOpen && searchable && searchInputRef.current) {
      searchInputRef.current.focus();
    }
    if (!isOpen) {
      setSearchQuery('');
    }
  }, [isOpen, searchable]);

  // Filter options based on search query
  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) return options;
    const query = searchQuery.toLowerCase();
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(query) ||
        opt.description?.toLowerCase().includes(query)
    );
  }, [options, searchQuery]);

  const selectedOption = options.find((opt) => opt.value === value);
  const displayLabel = selectedOption?.label || placeholder;
  const displayIcon = selectedOption?.icon || icon;

  const sizeStyles = {
    sm: 'px-2.5 py-1.5 text-xs',
    md: 'px-3 py-2 text-sm',
  };

  const handleSelect = (optionValue: T) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          inline-flex items-center justify-between gap-2 font-medium rounded-lg
          border border-gray-300 bg-white
          transition-all
          hover:bg-gray-50 hover:border-gray-400
          focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
          disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white disabled:hover:border-gray-300
          ${isOpen ? 'ring-2 ring-primary-500 border-transparent' : ''}
          ${sizeStyles[size]}
        `}
      >
        <span className="inline-flex items-center gap-2 min-w-0">
          {displayIcon && (
            <span className="flex-shrink-0 text-gray-500">{displayIcon}</span>
          )}
          <span className={`truncate ${!selectedOption ? 'text-gray-500' : 'text-gray-900'}`}>
            {displayLabel}
          </span>
        </span>
        <ChevronDown
          className={`w-4 h-4 flex-shrink-0 text-gray-400 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className={`
            absolute z-50 mt-1 min-w-[320px] max-w-[420px]
            bg-white rounded-xl shadow-xl border border-gray-200
            flex flex-col
            ${menuAlign === 'right' ? 'right-0' : 'left-0'}
          `}
          style={{ maxHeight: 'min(70vh, 480px)' }}
        >
          {/* Search Input */}
          {searchable && (
            <div className="p-2 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={searchPlaceholder}
                    className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
                {onRefresh && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRefresh();
                    }}
                    disabled={isRefreshing}
                    className="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors disabled:opacity-50 flex-shrink-0"
                    title="Refresh list"
                  >
                    <RotateCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Options List */}
          <div className="flex-1 overflow-auto py-1.5">
            {filteredOptions.map((option, index) => (
              <DropdownItem
                key={index}
                option={option}
                isSelected={option.value === value}
                onSelect={() => handleSelect(option.value)}
                menuAlign={menuAlign}
              />
            ))}

            {filteredOptions.length === 0 && (
              <div className="px-3 py-6 text-sm text-gray-500 text-center">
                {searchQuery ? 'No matching options' : 'No options available'}
              </div>
            )}
          </div>

          {/* Footer with count */}
          {searchable && options.length > 0 && (
            <div className="px-3 py-2 border-t border-gray-100 text-xs text-gray-400">
              {filteredOptions.length === options.length
                ? `${options.length} options`
                : `${filteredOptions.length} of ${options.length} options`}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
