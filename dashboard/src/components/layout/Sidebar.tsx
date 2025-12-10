import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Activity, Database, Settings, ChevronLeft, ChevronRight, MessageSquare, Server, Home } from 'lucide-react';

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
}

const navItems: NavItem[] = [
  { to: '/', icon: <Home className="w-5 h-5" />, label: 'Home' },
  { to: '/chat', icon: <MessageSquare className="w-5 h-5" />, label: 'Chat' },
  { to: '/sessions', icon: <Activity className="w-5 h-5" />, label: 'Agent Sessions' },
  { to: '/context-store', icon: <Database className="w-5 h-5" />, label: 'Context Store' },
  { to: '/agents', icon: <Settings className="w-5 h-5" />, label: 'Agent Blueprints' },
  { to: '/launchers', icon: <Server className="w-5 h-5" />, label: 'Agent Launchers' },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`bg-white border-r border-gray-200 flex flex-col transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-56'
      }`}
    >
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
            title={collapsed ? item.label : undefined}
          >
            {item.icon}
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-gray-200">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <>
              <ChevronLeft className="w-5 h-5" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
