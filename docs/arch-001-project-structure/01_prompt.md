I intend to clean up this project by clearly defining the placement and responsibility of each component. The project centers on Agent Orchestration, hence the name "Agent Orchestrator Framework." Currently, the framework includes two Claude Code-specific plugins.

First is the **Agent Orchestrator Plugin**. This serves as the core plugin, containing the Python commands used to manage agent sessions (start, resume, check status, retrieve results) and list agent sessions and definitions.

Second is the **Document Sync Plugin**. This provides a Python client for pushing and pulling documents, facilitating document sharing between agents. It functions as a shared context where one agent can provide documents for another to read. This plugin currently includes a document server component that provides endpoints for document transfer. However, the current naming and positioning are suboptimal. The core concept is not merely document management, but rather context management via file sharing. A more appropriate name is needed to reflect this purpose.

The "skills" are designed as lightweight scripts allowing AI or coding agents to interact quickly without requiring a full MCP server. These should remain minimal in code size. As the framework has evolved, I am moving away from embedding heavy logic within these skills. Instead, logic should reside in the servers they interact with, treating the skills as thin clients. Initially, these skills contained core logic and Claude Agent SDK interactions, but I am now convinced we should shift this abstraction and indexing logic to the server side.

Initially, I placed everything, including servers, within the skills folder to ensure self-contained functionality. For example, the document server is currently located within the document plugin. However, since plugins are distributed via Claude Code, this approach is no longer aligned with my goals. I want the skills to act solely as an abstraction layer for server interaction.

Additionally, the Agent Orchestrator currently contains the MCP server. The MCP server is simply another interface for creating and managing agents. I believe the current dependency structure is incorrect; the MCP server acts as a wrapper calling commands. We need to restructure this so that both the MCP server and the commands interact with a common backend server that handles the actual agent logic, rather than having direct dependencies between them.

I believe the MCP server does not belong at the skill level. It should be positioned at the root level, as it represents an alternative method for interacting with the Agent Orchestrator Framework, distinct from the skills.

Another component is **Agent Orchestrator Observability**. Originally intended as an optional add-on for monitoring agent activity, it has evolved into a core feature handling agent session management. We currently only utilize its backend, as the frontend has been superseded by the new Agent Orchestration Frontend. Consequently, "Observability" is no longer an accurate name; it is a core component for session management. We should rename it, remove the unused frontend portion, and elevate the server component to the root level (removing the backend subfolder).

Next is the **Agent Orchestrator Backend**. This component handles specialized Agent Management, specifically hosting configurations for specialized agents.

Finally, there is the **Agent Orchestrator Frontend**. This application interacts with the Agent Orchestrator Backend (Agent Management), the Agent Orchestrator Observability Backend (Session Management), and the Document Server (within the Document Sync Plugin) for document interaction.

**Task:**

Your task is to analyze the current structure. Please review the provided communications, ignoring outdated information. The primary objective is to identify each component, reference its implementation folder, and propose clear, professional names. Consult with me to finalize a concise naming schema and terminology for component interactions.

Once the components are defined, we need to design a proper file structure and hierarchy, grouping elements by relevance to improve clarity. The current architecture is a confusing mix of services and skills. I require a cleaner architecture and a high-level architectural document describing the framework's purpose, component arrangement, and a proposed project file hierarchy. 