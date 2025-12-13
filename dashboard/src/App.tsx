import { RouterProvider } from 'react-router-dom';
import { WebSocketProvider, NotificationProvider, ChatProvider, SessionsProvider } from '@/contexts';
import { router } from './router';

function App() {
  return (
    <NotificationProvider>
      <WebSocketProvider>
        <SessionsProvider>
          <ChatProvider>
            <RouterProvider router={router} />
          </ChatProvider>
        </SessionsProvider>
      </WebSocketProvider>
    </NotificationProvider>
  );
}

export default App;
