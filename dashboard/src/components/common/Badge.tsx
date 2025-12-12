import React from 'react';
import { CheckCircle2, StopCircle, CircleDot, CircleOff, HelpCircle, Loader2 } from 'lucide-react';

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

// Status icon component with optional animation
function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'running':
      return (
        <span className="relative flex h-2 w-2 mr-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
      );
    case 'stopping':
      return <Loader2 className="w-3 h-3 mr-1 animate-spin" />;
    case 'finished':
      return <CheckCircle2 className="w-3 h-3 mr-1" />;
    case 'stopped':
      return <StopCircle className="w-3 h-3 mr-1" />;
    case 'active':
      return <CircleDot className="w-3 h-3 mr-1" />;
    case 'inactive':
      return <CircleOff className="w-3 h-3 mr-1" />;
    default:
      return <HelpCircle className="w-3 h-3 mr-1" />;
  }
}

// Status-specific badges
export function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { variant: BadgeVariant; label: string }> = {
    running: { variant: 'success', label: 'Running' },
    stopping: { variant: 'warning', label: 'Stopping' },
    finished: { variant: 'info', label: 'Finished' },
    stopped: { variant: 'danger', label: 'Stopped' },
    active: { variant: 'success', label: 'Active' },
    inactive: { variant: 'gray', label: 'Inactive' },
  };

  const config = statusConfig[status] || { variant: 'default', label: status };

  return (
    <Badge variant={config.variant}>
      <StatusIcon status={status} />
      {config.label}
    </Badge>
  );
}
