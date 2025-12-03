import { RouterProvider } from 'react-router-dom';
import { WebSocketProvider, NotificationProvider, ChatProvider } from '@/contexts';
import { router } from './router';

function App() {
  return (
    <NotificationProvider>
      <WebSocketProvider>
        <ChatProvider>
          <RouterProvider router={router} />
        </ChatProvider>
      </WebSocketProvider>
    </NotificationProvider>
  );
}

export default App;
