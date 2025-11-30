import { createBrowserRouter } from 'react-router-dom';
import { Layout } from '@/components/layout';
import { AgentSessions, Documents, AgentManager } from '@/pages';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <AgentSessions />,
      },
      {
        path: 'documents',
        element: <Documents />,
      },
      {
        path: 'agents',
        element: <AgentManager />,
      },
    ],
  },
]);
