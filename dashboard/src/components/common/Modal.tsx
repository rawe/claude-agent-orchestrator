import React, { Fragment } from 'react';
import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from '@headlessui/react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
}

const sizeStyles = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  '2xl': 'max-w-6xl',
  full: 'max-w-7xl',
};

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </TransitionChild>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <TransitionChild
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <DialogPanel
                className={`relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 w-full ${sizeStyles[size]}`}
              >
                {title && (
                  <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                    <DialogTitle as="h3" className="text-lg font-semibold text-gray-900">
                      {title}
                    </DialogTitle>
                    <button
                      onClick={onClose}
                      className="text-gray-400 hover:text-gray-500 focus:outline-none"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                )}
                <div className={title ? '' : 'pt-4'}>{children}</div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  loading?: boolean;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger',
  loading = false,
}: ConfirmModalProps) {
  const confirmButtonStyle =
    variant === 'danger'
      ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
      : variant === 'warning'
        ? 'bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500'
        : 'bg-primary-600 hover:bg-primary-700 focus:ring-primary-500';

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <div className="px-6 py-4">
        <p className="text-sm text-gray-500">{message}</p>
      </div>
      <div className="flex justify-end gap-3 px-6 py-4 bg-gray-50">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
          disabled={loading}
        >
          {cancelText}
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className={`px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 ${confirmButtonStyle}`}
        >
          {loading ? 'Processing...' : confirmText}
        </button>
      </div>
    </Modal>
  );
}
