import { WebSocketProvider } from './contexts/WebSocketContext';
import { ChatProvider } from './contexts/ChatContext';
import { Chat } from './components/Chat';

function App() {
  return (
    <WebSocketProvider>
      <ChatProvider>
        <Chat />
      </ChatProvider>
    </WebSocketProvider>
  );
}

export default App;
