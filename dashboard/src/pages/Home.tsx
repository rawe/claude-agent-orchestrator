import { Link } from 'react-router-dom';
import { MessageSquare, Activity, Settings, Server, ArrowDown, Database, Zap } from 'lucide-react';

export function Home() {
  return (
    <div className="min-h-full bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 overflow-auto">
      {/* Hero Section */}
      <div className="px-8 py-16 bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold mb-6 tracking-tight">
            Agent Orchestration Framework
          </h1>
          <p className="text-xl text-indigo-100 max-w-3xl mx-auto leading-relaxed">
            A powerful framework for orchestrating AI agents with Claude Code.
            Create specialized agent teams, coordinate work through callbacks,
            and share context across isolated sessions.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link
              to="/chat"
              className="px-6 py-3 bg-white text-indigo-600 rounded-lg font-semibold hover:bg-indigo-50 transition-colors"
            >
              Start Chatting
            </Link>
            <Link
              to="/agents"
              className="px-6 py-3 bg-indigo-500 text-white rounded-lg font-semibold hover:bg-indigo-400 transition-colors border border-indigo-400"
            >
              Configure Agents
            </Link>
          </div>
        </div>
      </div>

      {/* Key Capabilities */}
      <div className="px-8 py-12 bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Settings className="w-6 h-6 text-indigo-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">Agent Blueprints</h3>
              <p className="text-sm text-gray-500">Define reusable agent configurations with custom prompts and MCP servers</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Zap className="w-6 h-6 text-orange-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">Callback Coordination</h3>
              <p className="text-sm text-gray-500">Parent agents spawn workers and receive automatic completion notifications</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Database className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">Context Sharing</h3>
              <p className="text-sm text-gray-500">Share documents between isolated agent sessions via the context store</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Activity className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">Real-time Monitoring</h3>
              <p className="text-sm text-gray-500">Live WebSocket updates for session events, status, and results</p>
            </div>
          </div>
        </div>
      </div>

      {/* Architecture Overview */}
      <div className="px-8 py-12">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-semibold text-gray-900 mb-2 text-center">
            Architecture Overview
          </h2>
          <p className="text-gray-500 text-center mb-8 max-w-2xl mx-auto">
            The framework consists of a central coordinator, distributed launchers, and a context store
            working together to manage agent sessions.
          </p>

          {/* Architecture Diagram */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8 mb-12">
            <div className="flex flex-col items-center gap-4">
              {/* User Layer */}
              <div className="flex flex-wrap justify-center gap-3">
                <div className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium border border-slate-200">
                  Claude Code
                </div>
                <div className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium border border-slate-200">
                  Claude Desktop
                </div>
                <div className="px-4 py-2 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-medium border border-indigo-200">
                  Dashboard (You are here)
                </div>
              </div>

              <ArrowDown className="w-5 h-5 text-gray-400" />

              {/* API Layer */}
              <div className="w-full max-w-2xl">
                <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl p-6 text-white">
                  <div className="text-center mb-4">
                    <h3 className="font-bold text-lg">Agent Coordinator</h3>
                    <p className="text-indigo-100 text-sm">Central orchestration service</p>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                    <div className="bg-white/20 rounded px-2 py-1.5 text-center">Sessions API</div>
                    <div className="bg-white/20 rounded px-2 py-1.5 text-center">Jobs Queue</div>
                    <div className="bg-white/20 rounded px-2 py-1.5 text-center">Blueprints</div>
                    <div className="bg-white/20 rounded px-2 py-1.5 text-center">Callbacks</div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-8 w-full max-w-2xl">
                <div className="flex-1 h-px bg-gray-300"></div>
                <span className="text-xs text-gray-400 whitespace-nowrap">long-poll / WebSocket</span>
                <div className="flex-1 h-px bg-gray-300"></div>
              </div>

              {/* Execution Layer */}
              <div className="flex flex-wrap justify-center gap-6 w-full">
                {/* Launcher */}
                <div className="bg-teal-50 border-2 border-teal-200 rounded-xl p-5 min-w-[200px]">
                  <div className="text-center">
                    <div className="w-10 h-10 bg-teal-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                      <Server className="w-5 h-5 text-teal-600" />
                    </div>
                    <h4 className="font-semibold text-teal-800 text-sm">Agent Launcher</h4>
                    <p className="text-teal-600 text-xs mt-1">Executes Claude Code sessions</p>
                  </div>
                </div>

                {/* Context Store */}
                <div className="bg-purple-50 border-2 border-purple-200 rounded-xl p-5 min-w-[200px]">
                  <div className="text-center">
                    <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                      <Database className="w-5 h-5 text-purple-600" />
                    </div>
                    <h4 className="font-semibold text-purple-800 text-sm">Context Store</h4>
                    <p className="text-purple-600 text-xs mt-1">Shared document storage</p>
                  </div>
                </div>
              </div>

              <ArrowDown className="w-5 h-5 text-gray-400" />

              {/* Agent Sessions */}
              <div className="flex flex-wrap justify-center gap-3">
                <div className="px-4 py-3 bg-green-100 text-green-700 rounded-lg text-sm font-medium border border-green-200 flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  Orchestrator Session
                </div>
              </div>

              <div className="flex items-center gap-2 text-gray-400">
                <div className="w-8 h-px bg-gray-300"></div>
                <span className="text-xs">spawns with callback</span>
                <div className="w-8 h-px bg-gray-300"></div>
              </div>

              {/* Specialized Agents */}
              <div className="flex flex-wrap justify-center gap-3">
                <div className="px-3 py-2 bg-emerald-100 text-emerald-700 rounded-lg text-sm font-medium border border-emerald-200">
                  Worker Agent
                </div>
                <div className="px-3 py-2 bg-emerald-100 text-emerald-700 rounded-lg text-sm font-medium border border-emerald-200">
                  Worker Agent
                </div>
                <div className="px-3 py-2 bg-emerald-100 text-emerald-700 rounded-lg text-sm font-medium border border-emerald-200">
                  Worker Agent
                </div>
              </div>

              <ArrowDown className="w-5 h-5 text-gray-400" />

              {/* MCP Servers */}
              <div className="flex flex-wrap justify-center gap-2">
                <div className="px-3 py-1.5 bg-orange-100 text-orange-700 rounded text-xs border border-orange-200">
                  Atlassian MCP
                </div>
                <div className="px-3 py-1.5 bg-orange-100 text-orange-700 rounded text-xs border border-orange-200">
                  Neo4j MCP
                </div>
                <div className="px-3 py-1.5 bg-orange-100 text-orange-700 rounded text-xs border border-orange-200">
                  ADO MCP
                </div>
                <div className="px-3 py-1.5 bg-orange-100 text-orange-700 rounded text-xs border border-orange-200">
                  Custom MCP
                </div>
              </div>
            </div>
          </div>

          {/* Component Cards */}
          <h2 className="text-2xl font-semibold text-gray-900 mb-2 text-center">
            Dashboard Components
          </h2>
          <p className="text-gray-500 text-center mb-8">
            Navigate the framework using these sections
          </p>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Chat */}
            <Link
              to="/chat"
              className="group bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg hover:border-indigo-300 hover:-translate-y-1 transition-all"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2.5 bg-indigo-100 rounded-xl group-hover:bg-indigo-200 transition-colors">
                  <MessageSquare className="w-5 h-5 text-indigo-600" />
                </div>
                <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors">Chat</h3>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">
                Start new agent sessions with prompts. Select an agent blueprint,
                enter your task, and launch a new Claude Code session.
              </p>
            </Link>

            {/* Sessions */}
            <Link
              to="/sessions"
              className="group bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg hover:border-green-300 hover:-translate-y-1 transition-all"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2.5 bg-green-100 rounded-xl group-hover:bg-green-200 transition-colors">
                  <Activity className="w-5 h-5 text-green-600" />
                </div>
                <h3 className="font-semibold text-gray-900 group-hover:text-green-600 transition-colors">Agent Sessions</h3>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">
                Monitor running and completed sessions in real-time. View event
                timelines, session status, and execution results.
              </p>
            </Link>

            {/* Context Store */}
            <Link
              to="/context-store"
              className="group bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg hover:border-purple-300 hover:-translate-y-1 transition-all"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2.5 bg-purple-100 rounded-xl group-hover:bg-purple-200 transition-colors">
                  <Database className="w-5 h-5 text-purple-600" />
                </div>
                <h3 className="font-semibold text-gray-900 group-hover:text-purple-600 transition-colors">Context Store</h3>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">
                Manage shared documents that agents can access. Push and pull
                documents to share information across isolated sessions.
              </p>
            </Link>

            {/* Agent Blueprints */}
            <Link
              to="/agents"
              className="group bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg hover:border-indigo-300 hover:-translate-y-1 transition-all"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2.5 bg-indigo-100 rounded-xl group-hover:bg-indigo-200 transition-colors">
                  <Settings className="w-5 h-5 text-indigo-600" />
                </div>
                <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors">Agent Blueprints</h3>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">
                Create and configure agent blueprints. Define system prompts,
                assign MCP servers, and set agent capabilities.
              </p>
            </Link>

            {/* Agent Launchers */}
            <Link
              to="/launchers"
              className="group bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg hover:border-teal-300 hover:-translate-y-1 transition-all"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2.5 bg-teal-100 rounded-xl group-hover:bg-teal-200 transition-colors">
                  <Server className="w-5 h-5 text-teal-600" />
                </div>
                <h3 className="font-semibold text-gray-900 group-hover:text-teal-600 transition-colors">Agent Launchers</h3>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">
                View registered launchers and their health status. Launchers
                execute agent sessions as Claude Code subprocesses.
              </p>
            </Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="px-8 py-8 border-t border-gray-200 bg-white">
        <div className="max-w-5xl mx-auto text-center">
          <p className="text-sm text-gray-500">
            Built with Claude Code Agent SDK
          </p>
        </div>
      </div>
    </div>
  );
}
