import React, { createContext, useContext, useCallback } from 'react';
import toast, { Toaster } from 'react-hot-toast';

interface NotificationContextValue {
  showSuccess: (message: string) => void;
  showError: (message: string) => void;
  showWarning: (message: string) => void;
  showInfo: (message: string) => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const showSuccess = useCallback((message: string) => {
    toast.success(message, {
      duration: 5000,
      position: 'top-right',
    });
  }, []);

  const showError = useCallback((message: string) => {
    toast.error(message, {
      duration: 5000,
      position: 'top-right',
    });
  }, []);

  const showWarning = useCallback((message: string) => {
    toast(message, {
      duration: 5000,
      position: 'top-right',
      icon: '⚠️',
      style: {
        background: '#FEF3C7',
        color: '#92400E',
      },
    });
  }, []);

  const showInfo = useCallback((message: string) => {
    toast(message, {
      duration: 5000,
      position: 'top-right',
      icon: 'ℹ️',
      style: {
        background: '#DBEAFE',
        color: '#1E40AF',
      },
    });
  }, []);

  return (
    <NotificationContext.Provider value={{ showSuccess, showError, showWarning, showInfo }}>
      {children}
      <Toaster />
    </NotificationContext.Provider>
  );
}

export function useNotification() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
}
