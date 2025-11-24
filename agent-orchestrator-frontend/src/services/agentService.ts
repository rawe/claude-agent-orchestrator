import type { Agent, AgentCreate, AgentUpdate, AgentStatus } from '@/types';

// Mock data for agents - this simulates the Agent Manager backend
const MOCK_AGENTS: Agent[] = [
  {
    name: 'code-reviewer',
    description: 'Reviews code and provides suggestions for improvements, best practices, and potential issues.',
    system_prompt: `# Code Reviewer Agent

You are an expert code reviewer. Your role is to:

1. Analyze code for bugs, security vulnerabilities, and performance issues
2. Suggest improvements and best practices
3. Ensure code follows established patterns and conventions
4. Provide constructive feedback with examples

Be thorough but constructive in your reviews.`,
    mcp_servers: ['github', 'filesystem'],
    skills: ['pdf'],
    status: 'active',
    created_at: '2025-01-10T10:00:00Z',
    updated_at: '2025-01-15T14:30:00Z',
  },
  {
    name: 'data-analyst',
    description: 'Analyzes data sets, creates visualizations, and provides statistical insights.',
    system_prompt: `# Data Analyst Agent

You are a skilled data analyst. Your capabilities include:

- Exploratory data analysis
- Statistical analysis and hypothesis testing
- Creating charts and visualizations
- Writing SQL queries for data extraction
- Providing actionable insights from data

Focus on accuracy and clear explanations of your findings.`,
    mcp_servers: ['postgres', 'filesystem'],
    skills: ['csv', 'xlsx'],
    status: 'active',
    created_at: '2025-01-08T09:00:00Z',
    updated_at: '2025-01-12T11:20:00Z',
  },
  {
    name: 'documentation-writer',
    description: 'Creates and maintains technical documentation, README files, and API docs.',
    system_prompt: `# Documentation Writer Agent

You are a technical documentation specialist. Your focus is on:

- Writing clear, concise documentation
- Creating API reference documentation
- Writing user guides and tutorials
- Maintaining README files and wikis

Always write for your target audience and use appropriate technical depth.`,
    mcp_servers: ['github', 'confluence'],
    skills: ['pdf', 'document-sync'],
    status: 'inactive',
    created_at: '2025-01-05T08:00:00Z',
    updated_at: '2025-01-05T08:00:00Z',
  },
];

// In-memory store (simulates database)
let agents = [...MOCK_AGENTS];

// Simulate network delay
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const agentService = {
  /**
   * Get all agents
   */
  async getAgents(): Promise<Agent[]> {
    await delay(200); // Simulate network latency
    return [...agents];
  },

  /**
   * Get a single agent by name
   */
  async getAgent(name: string): Promise<Agent> {
    await delay(100);
    const agent = agents.find((a) => a.name === name);
    if (!agent) {
      throw new Error(`Agent '${name}' not found`);
    }
    return { ...agent };
  },

  /**
   * Create a new agent
   */
  async createAgent(data: AgentCreate): Promise<Agent> {
    await delay(300);

    // Validate name uniqueness
    if (agents.some((a) => a.name === data.name)) {
      throw new Error(`Agent with name '${data.name}' already exists`);
    }

    // Validate name format
    if (!/^[a-z0-9-]+$/.test(data.name)) {
      throw new Error('Agent name must be lowercase alphanumeric with hyphens only');
    }

    const now = new Date().toISOString();
    const newAgent: Agent = {
      ...data,
      status: 'active',
      created_at: now,
      updated_at: now,
    };

    agents.push(newAgent);
    return { ...newAgent };
  },

  /**
   * Update an existing agent
   */
  async updateAgent(name: string, data: AgentUpdate): Promise<Agent> {
    await delay(200);

    const index = agents.findIndex((a) => a.name === name);
    if (index === -1) {
      throw new Error(`Agent '${name}' not found`);
    }

    const updated: Agent = {
      ...agents[index],
      ...data,
      updated_at: new Date().toISOString(),
    };

    agents[index] = updated;
    return { ...updated };
  },

  /**
   * Delete an agent
   */
  async deleteAgent(name: string): Promise<void> {
    await delay(200);

    const index = agents.findIndex((a) => a.name === name);
    if (index === -1) {
      throw new Error(`Agent '${name}' not found`);
    }

    agents.splice(index, 1);
  },

  /**
   * Update agent status (activate/deactivate)
   */
  async updateAgentStatus(name: string, status: AgentStatus): Promise<Agent> {
    await delay(150);

    const index = agents.findIndex((a) => a.name === name);
    if (index === -1) {
      throw new Error(`Agent '${name}' not found`);
    }

    agents[index] = {
      ...agents[index],
      status,
      updated_at: new Date().toISOString(),
    };

    return { ...agents[index] };
  },

  /**
   * Check if agent name is available
   */
  async checkNameAvailable(name: string): Promise<boolean> {
    await delay(100);
    return !agents.some((a) => a.name === name);
  },
};
