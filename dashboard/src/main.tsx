import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

// Note: StrictMode temporarily disabled for debugging duplicate messages issue
// Re-enable after fixing: wrap <App /> with <StrictMode>
createRoot(document.getElementById('root')!).render(<App />);
