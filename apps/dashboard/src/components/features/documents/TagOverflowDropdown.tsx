import { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';

interface TagOverflowDropdownProps {
  tags: { name: string; count: number }[];
  selectedTags: string[];
  onToggle: (tag: string) => void;
}

export function TagOverflowDropdown({ tags, selectedTags, onToggle }: TagOverflowDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedCount = tags.filter(t => selectedTags.includes(t.name)).length;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-2.5 py-1 text-xs rounded-full bg-white border border-gray-200
                   text-gray-600 hover:border-gray-300 flex items-center gap-1"
      >
        +{tags.length} more
        {selectedCount > 0 && (
          <span className="bg-primary-100 text-primary-700 px-1.5 rounded-full">
            {selectedCount}
          </span>
        )}
        <ChevronDown className="w-3 h-3" />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200
                        rounded-md shadow-lg py-1 z-10 min-w-[160px] max-h-[240px] overflow-y-auto">
          {tags.map((tag) => (
            <button
              key={tag.name}
              onClick={() => onToggle(tag.name)}
              className={`w-full px-3 py-1.5 text-left text-sm flex justify-between
                         hover:bg-gray-50 ${
                           selectedTags.includes(tag.name)
                             ? 'text-primary-700 font-medium'
                             : 'text-gray-700'
                         }`}
            >
              <span>{tag.name}</span>
              <span className="text-gray-400">({tag.count})</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
