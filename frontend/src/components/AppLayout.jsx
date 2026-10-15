import Navbar from './Navbar';
import './AppLayout.css';

export default function AppLayout({ children }) {
  return (
    <div className="app-layout">
      <Navbar />
      <main className="app-layout__main" id="main-content">
        {children}
      </main>
    </div>
  );
}
