import { RouterProvider } from 'react-router-dom';
import { SSEProvider, NotificationProvider, ChatProvider, SessionsProvider } from '@/contexts';
import { router } from './router';

function App() {
  return (
    <NotificationProvider>
      <SSEProvider>
        <SessionsProvider>
          <ChatProvider>
            <RouterProvider router={router} />
          </ChatProvider>
        </SessionsProvider>
      </SSEProvider>
    </NotificationProvider>
  );
}

export default App;
