# ZenoMind - Architecture Guide

## System Architecture Overview

ZenoMind is a sophisticated ambient AI agent system built with a modern, scalable architecture emphasizing modularity, extensibility, and production-readiness.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │   React UI   │  │  WebSocket   │  │   REST API Clients  │   │
│  │  Dashboard   │  │   Clients    │  │   (Python, JS, etc) │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway Layer                            │
│                     (FastAPI Server)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   REST API   │  │  WebSocket   │  │   CORS Middleware    │ │
│  │  Endpoints   │  │   Handler    │  │                      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Task Management & Orchestration                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │ │
│  │  │ Task Queue   │  │   Ambient    │  │    Plugin      │  │ │
│  │  │  Manager     │  │    Agent     │  │    Manager     │  │ │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Learning & Intelligence Layer                  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │ │
│  │  │   Pattern    │  │  Strategy    │  │  Experience    │  │ │
│  │  │  Recognizer  │  │  Optimizer   │  │    Replay      │  │ │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 Observability Layer                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │ │
│  │  │Consciousness │  │   Metrics    │  │     Error      │  │ │
│  │  │  Streamer    │  │  Collector   │  │    Handler     │  │ │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Persistence Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   SQLAlchemy │  │   ChromaDB   │  │      Redis           │ │
│  │   Database   │  │Vector Memory │  │   (Task Queue)       │ │
│  │   (SQLite/PG)│  │              │  │                      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   External Services Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   OpenManus  │  │  Playwright  │  │   LLM APIs           │ │
│  │   Framework  │  │   Browser    │  │(OpenAI, Anthropic)   │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. API Gateway Layer

**Technology**: FastAPI with async/await

**Responsibilities**:
- HTTP REST API endpoints
- WebSocket connection management
- Request validation (Pydantic)
- CORS handling
- Request/response transformation

**Key Files**:
- `backend/main.py` - Main application entry point
- API route handlers
- Middleware configuration

### 2. Task Management System

**Components**:

#### Task Queue (`backend/tasks/queue.py`)
- Async task queue for long-running operations
- Priority-based scheduling
- Timeout management
- Task cancellation support

#### Ambient Agent (`backend/agents/ambient.py`)
- Wraps OpenManus agent framework
- Manages task execution lifecycle
- Integrates consciousness streaming
- Handles memory storage
- Implements auto-learning

#### Enhanced Browser (`backend/agents/browser.py`)
- Multi-tab browser management
- Intelligent tab switching
- Context preservation
- Screenshot capture
- LRU tab eviction

### 3. Learning System

**Architecture**: Multi-component learning pipeline

#### Pattern Recognizer (`backend/learning/pattern_recognizer.py`)
```
Input: Task Description + Outcome
  │
  ├─> Keyword Pattern Matching
  ├─> Structural Pattern Detection
  ├─> Semantic Pattern Analysis
  │
  ▼
Output: Pattern IDs + Success Correlation
```

**Features**:
- Real-time pattern extraction
- Success rate tracking per pattern
- Optimal tool sequence learning
- Pattern-based recommendations

#### Strategy Optimizer (`backend/learning/strategy_optimizer.py`)
```
Multi-Armed Bandit (UCB Algorithm)
  │
  ├─> Exploration (ε-greedy)
  ├─> Exploitation (UCB scoring)
  ├─> Performance tracking
  │
  ▼
Adaptive Strategy Selection
```

**Features**:
- Upper Confidence Bound strategy selection
- Automatic performance optimization
- Dynamic exploration/exploitation balance
- Strategy performance metrics

#### Experience Replay (`backend/learning/experience_replay.py`)
```
Experience Buffer (Max 10,000)
  │
  ├─> Prioritized Sampling
  ├─> Reward Calculation
  ├─> Batch Retrieval
  │
  ▼
Learning from Past Experiences
```

**Features**:
- Circular buffer with prioritization
- Higher priority for failures and rare patterns
- Automatic reward signal generation
- Experience deduplication

#### Learning Engine (`backend/learning/learning_engine.py`)
```
Task Completion
  │
  ├─> Pattern Recognition
  ├─> Strategy Performance Update
  ├─> Experience Storage
  ├─> Batch Learning (every 10 tasks)
  │
  ▼
Continuous Improvement
```

### 4. Plugin System

**Architecture**: Dynamic module loading with lifecycle management

```
Plugin Discovery
  │
  ├─> File System Scan
  ├─> Import & Validation
  ├─> Registration
  │
  ▼
Plugin Manager
  │
  ├─> Load/Unload
  ├─> Enable/Disable
  ├─> Health Monitoring
  │
  ▼
Plugin Registry (Global)
```

**Components**:

- `plugins/base.py` - Base plugin classes
- `plugins/manager.py` - Lifecycle management
- `plugins/loader.py` - Dynamic discovery
- `plugins/registry.py` - Global registry

**Plugin Types**:
1. **ToolPlugin**: Executable functions
2. **DataSourcePlugin**: Data access
3. **IntegrationPlugin**: External services

### 5. Database Layer

**Technology**: SQLAlchemy with async support

**Architecture**:

```
Application Code
  │
  ├─> Repository Layer (Clean API)
  │     └─> TaskRepository
  │     └─> AgentRepository
  │     └─> MetricRepository
  │     └─> MemoryRepository
  │
  ├─> ORM Models
  │     └─> Task, Agent, Metric, Memory, Plugin
  │
  ├─> Connection Manager
  │     └─> Async Session Factory
  │     └─> Connection Pooling
  │
  ▼
Database (SQLite/PostgreSQL/MySQL)
```

**Key Features**:
- Repository pattern for clean separation
- Async sessions with proper lifecycle
- Multi-index optimization
- Automatic migrations support
- Transaction management

**Models**:

```python
Task
├─ task_id (unique)
├─ prompt, priority, status
├─ progress, result, error
├─ timestamps (created, started, completed)
└─ relationships → Agent

Agent
├─ agent_id (unique)
├─ performance metrics
├─ learning metrics
└─ relationships → Tasks, Metrics

Metric
├─ metric_name, value, type
├─ labels (JSON)
├─ timestamps
└─ relationships → Agent

Memory
├─ memory_id (unique)
├─ content, content_hash
├─ metadata, importance
└─ access tracking

Plugin
├─ plugin_id (unique)
├─ configuration
└─ usage statistics
```

### 6. Consciousness Streaming

**Architecture**: Event-driven streaming with WebSocket

```
Agent Thoughts/Actions
  │
  ├─> ConsciousnessEvent Creation
  │     └─ Type: thought, action, emotion, etc.
  │
  ├─> Event Buffer (Circular, 100 items)
  │
  ├─> Broadcast to Subscribers
  │     └─ WebSocket Connections
  │
  ▼
Real-time Client Updates
```

**Event Types**:
- **thought**: Reasoning and planning
- **action**: Tool executions
- **observation**: Results
- **reflection**: Self-assessment
- **emotion**: Emotional states
- **progress**: Task progress
- **insight**: Discoveries

**Emotional State Tracking**:

```
Context Analysis
  │
  ├─> Infer Emotion
  │     └─ Based on: progress, errors, complexity
  │
  ├─> Update State
  │     └─ Emotion, intensity, reason
  │
  ├─> State History
  │     └─ Pattern analysis
  │
  ▼
Emotional Insights
```

### 7. Error Handling System

**Architecture**: Layered error handling with recovery

```
Error Occurs
  │
  ├─> Error Categorization
  │     └─ Network, Database, Validation, etc.
  │
  ├─> Severity Classification
  │     └─ Low, Medium, High, Critical
  │
  ├─> Structured Logging
  │     └─ Context, stacktrace, metadata
  │
  ├─> Recovery Attempt
  │     └─ Category-specific strategies
  │
  ├─> Retry Logic (if applicable)
  │     └─ Exponential backoff + jitter
  │
  ▼
Error Resolution or Escalation
```

**Retry Strategy**:

```
Attempt 1: Initial delay (1s)
Attempt 2: 2s (exponential: 2^1)
Attempt 3: 4s (exponential: 2^2)
Attempt 4: 8s (exponential: 2^3)
Attempt 5: 16s (exponential: 2^4)
         + Jitter (randomization)
         + Max delay cap (60s)
```

### 8. Metrics & Analytics

**Architecture**: Time-series metrics with aggregation

```
Metric Collection Points
  │
  ├─> Task Events
  ├─> Agent Performance
  ├─> System Health
  │
  ▼
Metric Repository
  │
  ├─> Time-series Storage
  ├─> Aggregation Functions
  ├─> Query Optimization
  │
  ▼
Analytics & Visualization
```

**Metric Types**:
- **counter**: Cumulative counts
- **gauge**: Point-in-time values
- **histogram**: Distribution of values

**Aggregations**:
- avg, sum, min, max, count
- Windowed aggregations
- Agent-level rollups

## Data Flow

### Task Execution Flow

```
1. Client creates task via REST API
   POST /api/tasks

2. API validates request (Pydantic)

3. Task persisted to database
   TaskRepository.create()

4. Task added to queue
   asyncio.create_task(execute_task)

5. Agent executes task
   └─> Consciousness streaming (WebSocket)
   └─> Pattern recognition
   └─> Memory storage
   └─> Metrics collection

6. Task completion
   └─> Database update
   └─> Strategy performance update
   └─> Experience storage
   └─> Client notification
```

### Learning Flow

```
1. Task Completion
   │
2. Pattern Recognizer analyzes task
   └─> Identifies patterns
   └─> Updates pattern statistics

3. Strategy Optimizer updates performance
   └─> Calculates reward
   └─> Updates exploitation value

4. Experience Replay stores experience
   └─> Calculates priority
   └─> Adds to buffer

5. Batch Learning (every 10 tasks)
   └─> Sample experiences
   └─> Analyze patterns
   └─> Update strategies
```

### Plugin Lifecycle

```
1. Discovery
   PluginLoader.discover_plugins()
   └─> Scans plugin directories
   └─> Imports Python modules
   └─> Validates plugin classes

2. Registration
   PluginRegistry.register_class()
   └─> Stores in global registry

3. Loading
   PluginManager.load_plugin()
   └─> Instantiates plugin
   └─> Validates configuration
   └─> Calls initialize()

4. Enabling
   PluginManager.enable_plugin()
   └─> Calls on_enable()
   └─> Makes available to system

5. Execution
   plugin.execute()
   └─> Records usage metrics

6. Shutdown
   PluginManager.unload_plugin()
   └─> Calls on_disable()
   └─> Calls shutdown()
   └─> Cleanup resources
```

## Scalability Considerations

### Horizontal Scaling

**Stateless Design**:
- No server-side session state
- All state in database
- Cache invalidation strategy
- Distributed task queue ready (Redis)

**Load Balancing**:
```
    ┌─────────────┐
    │Load Balancer│
    └─────────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼───┐   ┌────▼────┐
│ API   │   │  API    │
│Server1│   │ Server2 │
└───┬───┘   └────┬────┘
    │            │
    └─────┬──────┘
          │
    ┌─────▼─────┐
    │  Shared   │
    │  Database │
    └───────────┘
```

### Database Scaling

**Vertical Scaling**:
- PostgreSQL for better concurrency
- Connection pooling
- Read replicas

**Horizontal Scaling**:
- Sharding by agent_id or task_id
- Separate metrics database
- Time-series database (TimescaleDB)

### Caching Strategy

**Multi-Level Cache**:

```
Level 1: In-Memory (Application)
  └─> Task cache (LRU)
  └─> Agent state cache
  └─> Plugin registry cache

Level 2: Redis (Distributed)
  └─> Session cache
  └─> Result cache
  └─> Rate limiting

Level 3: Database
  └─> Persistent storage
```

## Security Architecture

### Authentication & Authorization (Future)

```
Request
  │
  ├─> JWT Validation
  │     └─> Token verification
  │     └─> Claims extraction
  │
  ├─> Authorization Check
  │     └─> Role-based access control
  │     └─> Resource permissions
  │
  ├─> Rate Limiting
  │     └─> Per-user limits
  │     └─> Global limits
  │
  ▼
Protected Resource
```

### Data Protection

- Secrets management (environment variables)
- SQL injection prevention (parameterized queries)
- Input validation (Pydantic)
- CORS configuration
- API key rotation support

## Performance Optimization

### Database Optimization

**Indexes**:
```sql
-- Task queries
CREATE INDEX idx_status_created ON tasks(status, created_at);
CREATE INDEX idx_agent_status ON tasks(agent_id, status);

-- Metrics queries
CREATE INDEX idx_metric_timestamp ON metrics(metric_name, timestamp);
CREATE INDEX idx_agent_metric_timestamp ON metrics(agent_id, metric_name, timestamp);

-- Memory queries
CREATE INDEX idx_type_importance ON memories(memory_type, importance);
```

**Query Optimization**:
- Eager loading for common joins
- Pagination for large result sets
- Projection to fetch only needed columns
- Batch operations for bulk updates

### Async Performance

**Concurrency**:
- Non-blocking I/O throughout
- Async database operations
- Concurrent task execution
- Background workers for cleanup

**Resource Management**:
- Connection pooling
- Graceful shutdown
- Memory limits for buffers
- Automatic cleanup tasks

## Monitoring & Observability

### Logging Strategy

**Log Levels**:
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical failures

**Structured Logging**:
```python
logger.info(
    "Task completed",
    task_id="abc123",
    duration=45.2,
    success=True,
    agent_id="default"
)
```

### Metrics Collection

**System Metrics**:
- Task throughput (tasks/minute)
- Success rate (percentage)
- Average task duration
- Error rate by category
- Plugin usage statistics

**Business Metrics**:
- Patterns learned
- Strategies optimized
- Experiences stored
- Active agents
- Total task count

### Health Checks

```python
GET /
└─> Service status
└─> Active agents
└─> Active tasks
└─> Timestamp

GET /health (future)
└─> Database connectivity
└─> External service status
└─> Resource usage
```

## Deployment Architecture

### Development

```
Local Machine
  ├─> Frontend (Vite dev server) :3000
  ├─> Backend (Uvicorn) :8000
  ├─> SQLite database
  └─> ChromaDB local
```

### Production (Docker)

```
Docker Network
  ├─> Frontend Container (nginx)
  ├─> Backend Container (gunicorn + uvicorn)
  ├─> PostgreSQL Container
  ├─> Redis Container
  └─> ChromaDB Container
```

### Production (Kubernetes) - Future

```
Kubernetes Cluster
  ├─> Frontend Deployment (3 replicas)
  ├─> Backend Deployment (5 replicas)
  ├─> PostgreSQL StatefulSet
  ├─> Redis StatefulSet
  ├─> Ingress (load balancer)
  └─> Persistent Volumes
```

## Technology Stack Summary

### Backend
- **Framework**: FastAPI (async Python)
- **Database**: SQLAlchemy (async) + SQLite/PostgreSQL
- **Vector DB**: ChromaDB
- **Task Queue**: AsyncIO (upgradable to Dramatiq + Redis)
- **AI Framework**: OpenManus
- **Browser**: Playwright
- **Logging**: Loguru

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **State Management**: Zustand
- **Data Fetching**: TanStack Query
- **WebSocket**: Socket.io-client
- **Icons**: Lucide React

### DevOps
- **Containerization**: Docker + Docker Compose
- **Process Management**: Uvicorn (ASGI server)
- **Reverse Proxy**: nginx (production)

## Extension Points

### Adding New Features

1. **New API Endpoint**:
   - Add route handler in `main.py`
   - Create Pydantic models for request/response
   - Implement repository methods if database access needed

2. **New Plugin Type**:
   - Extend `Plugin` base class in `plugins/base.py`
   - Implement required abstract methods
   - Register in plugin manager

3. **New Learning Component**:
   - Add module in `backend/learning/`
   - Integrate with `LearningEngine`
   - Update task completion handler

4. **New Metric**:
   - Call `MetricRepository.record()` at collection point
   - Add API endpoint for retrieval
   - Update analytics dashboard

## Best Practices

### Code Organization
- One responsibility per module
- Clean interfaces (repository pattern)
- Dependency injection where applicable
- Type hints throughout
- Comprehensive docstrings

### Error Handling
- Specific exception classes
- Centralized error handler
- Structured logging with context
- Graceful degradation

### Testing Strategy (Future)
- Unit tests for business logic
- Integration tests for APIs
- E2E tests for critical flows
- Performance tests for scalability
- Mock external dependencies

### Documentation
- Code-level docstrings
- API documentation (auto-generated)
- Architecture documentation
- Deployment guides
- User guides

---

**Last Updated**: November 18, 2025
