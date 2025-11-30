import { RouterProvider } from 'react-router-dom';
import { WebSocketProvider, NotificationProvider } from '@/contexts';
import { router } from './router';

function App() {
  return (
    <NotificationProvider>
      <WebSocketProvider>
        <RouterProvider router={router} />
      </WebSocketProvider>
    </NotificationProvider>
  );
}

export default App;
