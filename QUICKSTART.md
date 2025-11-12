# ZenoMind - Quick Start Guide

Get ZenoMind up and running in 5 minutes!

## Prerequisites

- Python 3.12+
- Node.js 18+
- Git

## Installation

### 1. Clone the repository (if not already done)

```bash
git clone <your-repo-url>
cd zenomind-source
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
ANTHROPIC_API_KEY=your-key-here
# or
OPENAI_API_KEY=your-key-here
```

### 3. Install dependencies

```bash
# Install all dependencies (frontend + backend)
npm run install:all
```

Or manually:
```bash
# Frontend
npm install

# Backend
pip install -r backend/requirements.txt
```

### 4. Install Playwright browsers (for enhanced browser features)

```bash
playwright install chromium
```

## Running ZenoMind

### Option 1: Development Mode (Recommended for testing)

```bash
# This starts both frontend and backend
npm run dev
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Option 2: Docker (Recommended for production)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## First Steps

1. **Open the Dashboard** at http://localhost:3000

2. **Create your first task**:
   - Enter a prompt like: "Research the top 3 AI frameworks and compare them"
   - Click "Create Task"

3. **Watch the Consciousness Stream**:
   - Navigate to the "Consciousness" page
   - Watch the agent think in real-time as it works

4. **Monitor Tasks**:
   - Go to the "Tasks" page to see all running and completed tasks

5. **Explore Memory Palace**:
   - Visit "Memory Palace" to see what the agent has learned
   - Search semantically through memories

## Features at a Glance

### 🤖 Ambient Agent
- Runs continuously in the background
- Autonomous task execution
- Auto-learns from experiences

### 🌐 Enhanced Browser
- Multi-tab support (up to 10 tabs)
- Intelligent context management
- Screenshot capabilities

### ⏱️ Long-Task Execution
- Handles tasks up to hours long
- Distributed task queue
- Real-time progress updates

### 🧠 Consciousness Stream
**Signature Feature**: Watch the agent think!
- Real-time thought streaming
- See reasoning, actions, and reflections
- Emotion tracking

### 💾 Memory Palace
**Signature Feature**: Explore agent's knowledge!
- Vector similarity search
- Semantic memory retrieval
- Visual knowledge exploration

### 📊 Web Interface
- Beautiful React UI
- Real-time WebSocket updates
- Task visualization

## API Examples

### Create a task (Python)

```python
import requests

response = requests.post('http://localhost:8000/api/tasks', json={
    'prompt': 'Analyze the latest AI research papers',
    'priority': 'high',
    'max_duration': 3600,  # 1 hour
    'enable_browser': True
})

print(response.json())
```

### Create a task (JavaScript)

```javascript
const response = await fetch('http://localhost:8000/api/tasks', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: 'Analyze the latest AI research papers',
    priority: 'high',
    max_duration: 3600,
    enable_browser: true
  })
});

const data = await response.json();
console.log(data);
```

### WebSocket - Consciousness Stream

```javascript
import { io } from 'socket.io-client';

const socket = io('http://localhost:8000');

socket.on('consciousness', (event) => {
  console.log(`[${event.event_type}] ${event.content}`);
});
```

## Configuration

Edit `backend/config.toml` to customize:

- **LLM Model**: Change to GPT-4, Claude, or local models
- **Browser Settings**: Headless mode, max tabs
- **Task Settings**: Concurrent tasks, timeouts
- **Memory Settings**: Vector DB, max memories

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.12+

# Reinstall dependencies
pip install -r backend/requirements.txt

# Check logs
tail -f logs/zenomind.log
```

### Frontend won't start

```bash
# Check Node version
node --version  # Should be 18+

# Clear cache and reinstall
rm -rf node_modules
npm install
```

### Browser automation fails

```bash
# Reinstall Playwright
playwright install chromium
playwright install-deps
```

### Memory/ChromaDB issues

```bash
# Clear memory data
rm -rf data/memory
# The system will recreate on next start
```

## Architecture Overview

```
┌─────────────┐
│   React UI  │ ← WebSocket ← Consciousness Stream
└──────┬──────┘
       │ REST API
┌──────┴──────┐
│  FastAPI    │
│  Backend    │
└──────┬──────┘
       │
   ┌───┴────┬─────────┬──────────┐
   │        │         │          │
┌──┴──┐  ┌─┴──┐  ┌───┴───┐  ┌──┴───┐
│Manus│  │Task│  │Memory │  │Browser│
│Agent│  │Queue│  │Palace │  │Engine │
└─────┘  └────┘  └───────┘  └───────┘
```

## What Makes ZenoMind Special?

1. **Consciousness Stream**: Unlike other agents, you can watch ZenoMind think in real-time
2. **Memory Palace**: Visual exploration of agent's knowledge graph
3. **Auto-Learning**: Improves from experience across sessions
4. **Enhanced Browser**: Multi-tab browsing with context management
5. **Long Tasks**: Handles hours-long autonomous operations
6. **OpenManus Integration**: Built on a powerful, proven framework

## Next Steps

- Check out the [full README](README.md) for detailed information
- Explore the [OpenManus documentation](openmanus-source/README.md)
- Customize the system prompts in `openmanus-source/app/prompt/`
- Add custom tools to extend capabilities

## Need Help?

- Check the logs in `logs/zenomind.log`
- Open an issue on GitHub
- Review the OpenManus documentation

---

**Happy Ambient AI-ing!** ✨
