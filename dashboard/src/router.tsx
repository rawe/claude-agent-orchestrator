import { createBrowserRouter } from 'react-router-dom';
import { Layout } from '@/components/layout';
import { Home, AgentSessions, Documents, AgentManager, Capabilities, Runners, Chat, Runs, UnifiedView } from '@/pages';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Home />,
      },
      {
        path: 'chat',
        element: <Chat />,
      },
      {
        path: 'sessions',
        element: <AgentSessions />,
      },
      {
        path: 'runs',
        element: <Runs />,
      },
      {
        path: 'context-store',
        element: <Documents />,
      },
      {
        path: 'agents',
        element: <AgentManager />,
      },
      {
        path: 'capabilities',
        element: <Capabilities />,
      },
      {
        path: 'runners',
        element: <Runners />,
      },
      {
        path: 'unified',
        element: <UnifiedView />,
      },
    ],
  },
]);
