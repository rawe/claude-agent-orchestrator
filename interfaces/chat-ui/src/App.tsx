import { SSEProvider } from './contexts/SSEContext';
import { ChatProvider } from './contexts/ChatContext';
import { Chat } from './components/Chat';

function App() {
  return (
    <SSEProvider>
      <ChatProvider>
        <Chat />
      </ChatProvider>
    </SSEProvider>
  );
}

export default App;
