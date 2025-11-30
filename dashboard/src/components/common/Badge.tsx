import React from 'react';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'gray';
type BadgeSize = 'sm' | 'md';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
  gray: 'bg-gray-100 text-gray-600',
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2 py-1 text-xs',
};

export function Badge({ children, variant = 'default', size = 'sm', className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
}

// Status-specific badges
export function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { variant: BadgeVariant; label: string; icon: string }> = {
    running: { variant: 'success', label: 'Running', icon: '🟢' },
    finished: { variant: 'info', label: 'Finished', icon: '✅' },
    stopped: { variant: 'danger', label: 'Stopped', icon: '🛑' },
    active: { variant: 'success', label: 'Active', icon: '🟢' },
    inactive: { variant: 'gray', label: 'Inactive', icon: '⚫' },
  };

  const config = statusConfig[status] || { variant: 'default', label: status, icon: '❓' };

  return (
    <Badge variant={config.variant}>
      <span className="mr-1">{config.icon}</span>
      {config.label}
    </Badge>
  );
}
