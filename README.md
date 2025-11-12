# ZenoMind - Ambient AI Agent

> **An autonomous AI agent that thinks, browses, and executes complex tasks in the background**

ZenoMind is a next-generation ambient AI agent powered by OpenManus, designed to operate autonomously with enhanced browser capabilities, long-running task execution, and a beautiful web interface for monitoring its "consciousness stream."

## Features

### Core Capabilities
- **Ambient Operation**: Runs continuously in the background, ready to execute tasks
- **Enhanced Browser**: Multi-tab browsing with intelligent context management
- **Long-Task Execution**: Distributed task queue for hours-long operations
- **Real-time Monitoring**: Live stream of agent thoughts and actions
- **Web-Based UI**: Beautiful React interface with real-time updates

### Signature Features
- **Consciousness Stream**: Watch the agent think in real-time
- **Memory Palace**: Visual exploration of agent's learned knowledge
- **Auto-Learning**: Agent improves from experience across sessions
- **Task Visualization**: See complex tasks decompose and execute
- **Multi-Agent Orchestration**: Coordinate specialized agents for complex goals

### OpenManus Integration
Built on the powerful OpenManus framework with:
- ReAct reasoning pattern
- 10+ built-in tools (Python, Bash, Browser, Search, etc.)
- MCP (Model Context Protocol) support
- Multi-agent flows with planning
- Docker-based sandboxed execution

## Architecture

```
┌─────────────────────────────────────────────────┐
│           React Frontend (Vite)                 │
│  ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │
│  │Dashboard │ │  Tasks   │ │ Consciousness   │ │
│  │          │ │  Queue   │ │    Stream       │ │
│  └──────────┘ └──────────┘ └─────────────────┘ │
└────────────────┬────────────────────────────────┘
                 │ WebSocket + REST API
┌────────────────┴────────────────────────────────┐
│        FastAPI Backend Server                   │
│  ┌──────────────┐  ┌──────────────────────────┐ │
│  │   WebSocket  │  │   Task Queue (Dramatiq)  │ │
│  │   Manager    │  │   + Redis                │ │
│  └──────────────┘  └──────────────────────────┘ │
│  ┌──────────────────────────────────────────┐   │
│  │      OpenManus Agent Framework           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────┐  │   │
│  │  │  Manus  │ │ Browser │ │   Tools   │  │   │
│  │  │  Agent  │ │  Engine │ │Collection │  │   │
│  │  └─────────┘ └─────────┘ └───────────┘  │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   ┌──────────┐        ┌──────────────┐
   │Playwright│        │   ChromaDB   │
   │ Browser  │        │Vector Memory │
   └──────────┘        └──────────────┘
```

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Redis (for task queue)
- Docker (optional, for sandboxed execution)

### Installation

```bash
# Clone and install dependencies
npm run install:all

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys (OpenAI, Anthropic, etc.)

# Start services
npm run dev
```

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Usage

### Web Interface
Open http://localhost:3000 to access the dashboard.

1. **Create a Task**: Enter your goal in natural language
2. **Watch it Think**: See the consciousness stream in real-time
3. **Monitor Progress**: Track task decomposition and execution
4. **Explore Memory**: Visualize what the agent has learned

### API Examples

```python
import requests

# Create a task
response = requests.post('http://localhost:8000/api/tasks', json={
    'prompt': 'Research the top 5 AI papers from 2024 and create a summary',
    'priority': 'high',
    'max_duration': 3600  # 1 hour
})

task_id = response.json()['task_id']

# Get task status
status = requests.get(f'http://localhost:8000/api/tasks/{task_id}')
print(status.json())
```

### WebSocket Connection

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000');

// Subscribe to consciousness stream
socket.on('consciousness', (data) => {
  console.log('Agent thinking:', data.thought);
  console.log('Current action:', data.action);
});

// Subscribe to task updates
socket.on('task_update', (data) => {
  console.log('Task progress:', data.progress);
});
```

## Configuration

Edit `backend/config.toml` to customize:

```toml
[llm]
model = "claude-3-7-sonnet-20250219"
api_key = "your-api-key"
max_tokens = 8192

[browser]
headless = false
max_tabs = 5
screenshot_on_action = true

[tasks]
max_concurrent = 3
default_timeout = 1800
enable_auto_retry = true

[memory]
vector_db = "chromadb"
embedding_model = "all-MiniLM-L6-v2"
max_memories = 10000
```

## Signature Features Explained

### Consciousness Stream
Real-time visibility into the agent's reasoning process:
- **Thoughts**: See what the agent is considering
- **Actions**: Watch tool calls and decisions
- **Reflections**: Agent's self-assessment of progress

### Memory Palace
Visual exploration of the agent's knowledge graph:
- **Semantic Search**: Find related memories
- **Timeline View**: See learning progression
- **Connections**: Understand knowledge relationships

### Auto-Learning
The agent improves over time:
- **Experience Replay**: Learns from past successes/failures
- **Pattern Recognition**: Identifies common task types
- **Strategy Optimization**: Refines approach based on outcomes

## Project Structure

```
zenomind-source/
├── backend/                 # FastAPI backend
│   ├── main.py             # API server entry point
│   ├── config.toml         # Configuration
│   ├── agents/             # Agent implementations
│   │   ├── ambient.py      # Ambient agent wrapper
│   │   ├── browser.py      # Enhanced browser agent
│   │   └── orchestrator.py # Multi-agent coordinator
│   ├── tasks/              # Task queue workers
│   │   ├── queue.py        # Dramatiq setup
│   │   └── workers.py      # Task executors
│   ├── memory/             # Memory system
│   │   ├── vector_store.py # ChromaDB integration
│   │   └── palace.py       # Memory palace
│   ├── api/                # API routes
│   │   ├── tasks.py        # Task endpoints
│   │   ├── agents.py       # Agent management
│   │   └── memory.py       # Memory queries
│   └── websocket/          # WebSocket handlers
│       └── consciousness.py # Stream manager
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom hooks
│   │   ├── stores/         # Zustand stores
│   │   └── lib/            # Utilities
│   └── public/             # Static assets
├── openmanus-source/       # OpenManus framework
└── docker-compose.yml      # Docker orchestration
```

## Contributing

This is a custom implementation. Feel free to fork and adapt!

## License

MIT License - Built on top of OpenManus (MIT)

## Credits

- **OpenManus**: Core agent framework by MetaGPT team
- **Browser-Use**: Browser automation library
- **FastAPI**: Modern async Python web framework
- **React**: Frontend UI library

---

**Built with curiosity and a dash of ambient intelligence** ✨
