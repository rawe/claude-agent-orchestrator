import { useState } from 'react';
import { Badge } from '@/components/common';
import {
  Layers,
  Zap,
  GitBranch,
  AlignHorizontalDistributeCenter,
  Activity,
  LayoutGrid,
} from 'lucide-react';
import {
  TabId,
  SessionTimelineTab,
  RunCentricTab,
  TreeViewTab,
  SwimlaneTab,
  ActivityFeedTab,
  DashboardCardsTab,
} from './unified-view';

// ============================================================================
// TAB NAVIGATION
// ============================================================================

interface TabNavigationProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
  const tabs = [
    { id: 'session-timeline' as TabId, label: 'Session Timeline', icon: Layers, description: 'Sessions with run blocks' },
    { id: 'run-centric' as TabId, label: 'Run Centric', icon: Zap, description: 'Runs with session context' },
    { id: 'tree-view' as TabId, label: 'Tree View', icon: GitBranch, description: 'Hierarchical tree structure' },
    { id: 'swimlane' as TabId, label: 'Swimlane', icon: AlignHorizontalDistributeCenter, description: 'Gantt-style timeline view' },
    { id: 'activity-feed' as TabId, label: 'Activity Feed', icon: Activity, description: 'Unified chronological activity feed' },
    { id: 'dashboard-cards' as TabId, label: 'Dashboard Cards', icon: LayoutGrid, description: 'Grid/list of session cards with sparklines' },
  ];

  return (
    <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-lg">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all ${
              isActive
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            }`}
            title={tab.description}
          >
            <Icon className="w-4 h-4" />
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

// ============================================================================
// MAIN PAGE
// ============================================================================

export function UnifiedView() {
  const [activeTab, setActiveTab] = useState<TabId>('session-timeline');

  return (
    <div className="h-full flex flex-col">
      {/* Page Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-gray-900">Unified View</h1>
              <Badge variant="warning" size="sm">
                Mock
              </Badge>
            </div>
            <p className="text-sm text-gray-500">Compare different session/run visualization approaches</p>
          </div>
        </div>
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      {/* Tab Content */}
      {activeTab === 'session-timeline' && <SessionTimelineTab />}
      {activeTab === 'run-centric' && <RunCentricTab />}
      {activeTab === 'tree-view' && <TreeViewTab />}
      {activeTab === 'swimlane' && <SwimlaneTab />}
      {activeTab === 'activity-feed' && <ActivityFeedTab />}
      {activeTab === 'dashboard-cards' && <DashboardCardsTab />}
    </div>
  );
}
