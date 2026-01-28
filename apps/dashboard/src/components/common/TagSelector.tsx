import { useState, KeyboardEvent, useRef } from 'react';
import { X } from 'lucide-react';

interface TagSelectorProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function TagSelector({
  value,
  onChange,
  placeholder = 'Add tag...',
  disabled = false,
}: TagSelectorProps) {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const addTag = (tag: string) => {
    const trimmed = tag.trim().toLowerCase();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
    }
    setInputValue('');
  };

  const removeTag = (tagToRemove: string) => {
    onChange(value.filter((tag) => tag !== tagToRemove));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      if (inputValue.trim()) {
        addTag(inputValue);
      }
    } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      // Remove last tag when backspace is pressed on empty input
      removeTag(value[value.length - 1]);
    }
  };

  const handleBlur = () => {
    if (inputValue.trim()) {
      addTag(inputValue);
    }
  };

  return (
    <div
      className={`flex flex-wrap gap-1.5 p-2 min-h-[42px] border border-gray-300 rounded-md bg-white focus-within:ring-1 focus-within:ring-primary-500 focus-within:border-primary-500 ${
        disabled ? 'bg-gray-100 cursor-not-allowed' : 'cursor-text'
      }`}
      onClick={() => inputRef.current?.focus()}
    >
      {value.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 px-2 py-0.5 text-sm bg-primary-50 text-primary-700 rounded-md border border-primary-200"
        >
          {tag}
          {!disabled && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                removeTag(tag);
              }}
              className="hover:text-primary-900 focus:outline-none"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </span>
      ))}
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={value.length === 0 ? placeholder : ''}
        disabled={disabled}
        className="flex-1 min-w-[100px] outline-none text-sm bg-transparent disabled:cursor-not-allowed"
      />
    </div>
  );
}
