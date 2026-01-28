import { CheckCircle2, Clock, Loader2, XCircle, StopCircle, Zap } from 'lucide-react';
import type { RunStatus } from '@/types';

interface RunStatusBadgeProps {
  status: RunStatus;
  className?: string;
}

interface StatusConfig {
  bgColor: string;
  textColor: string;
  icon: React.ReactNode;
  label: string;
}

function getStatusConfig(status: RunStatus): StatusConfig {
  switch (status) {
    case 'pending':
      return {
        bgColor: 'bg-gray-100',
        textColor: 'text-gray-700',
        icon: <Clock className="w-3 h-3" />,
        label: 'Pending',
      };
    case 'claimed':
      return {
        bgColor: 'bg-blue-100',
        textColor: 'text-blue-700',
        icon: <Zap className="w-3 h-3" />,
        label: 'Claimed',
      };
    case 'running':
      return {
        bgColor: 'bg-emerald-100',
        textColor: 'text-emerald-700',
        icon: (
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
        ),
        label: 'Running',
      };
    case 'stopping':
      return {
        bgColor: 'bg-amber-100',
        textColor: 'text-amber-700',
        icon: <Loader2 className="w-3 h-3 animate-spin" />,
        label: 'Stopping',
      };
    case 'completed':
      return {
        bgColor: 'bg-green-100',
        textColor: 'text-green-700',
        icon: <CheckCircle2 className="w-3 h-3" />,
        label: 'Completed',
      };
    case 'failed':
      return {
        bgColor: 'bg-red-100',
        textColor: 'text-red-700',
        icon: <XCircle className="w-3 h-3" />,
        label: 'Failed',
      };
    case 'stopped':
      return {
        bgColor: 'bg-gray-100',
        textColor: 'text-gray-600',
        icon: <StopCircle className="w-3 h-3" />,
        label: 'Stopped',
      };
    default:
      return {
        bgColor: 'bg-gray-100',
        textColor: 'text-gray-600',
        icon: <Clock className="w-3 h-3" />,
        label: status,
      };
  }
}

export function RunStatusBadge({ status, className = '' }: RunStatusBadgeProps) {
  const config = getStatusConfig(status);

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full ${config.bgColor} ${config.textColor} ${className}`}
    >
      {config.icon}
      {config.label}
    </span>
  );
}
