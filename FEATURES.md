# ZenoMind - Advanced Features Documentation

This document describes the advanced features added to ZenoMind, transforming it into a production-ready ambient AI agent system.

## Table of Contents

1. [Database Persistence System](#database-persistence-system)
2. [Error Handling & Retry Logic](#error-handling--retry-logic)
3. [Plugin System](#plugin-system)
4. [Advanced Learning System](#advanced-learning-system)
5. [Enhanced Consciousness Streaming](#enhanced-consciousness-streaming)
6. [Metrics & Analytics](#metrics--analytics)
7. [API Reference](#api-reference)

---

## Database Persistence System

### Overview

ZenoMind now features a complete SQLAlchemy-based persistence layer that ensures data durability across server restarts and provides comprehensive metrics tracking.

### Features

#### Task Persistence
- **Automatic Recovery**: Tasks interrupted by server restarts are automatically resumed
- **State Tracking**: Complete task lifecycle tracking (queued, running, completed, failed, cancelled)
- **Result Storage**: Task results and errors are permanently stored
- **Progress Tracking**: Real-time progress updates persisted to database

#### Agent Metrics
- **Performance Tracking**: Success rates, average duration, total execution time
- **Learning Metrics**: Patterns learned, strategies optimized, experience count
- **Usage Statistics**: Task completion counts, failure analysis

#### Database Models

```python
from database.models import Task, Agent, Metric, Memory, Plugin

# Task model - Represents a single task
task = Task(
    task_id="unique-id",
    prompt="Research AI papers from 2024",
    priority=TaskPriority.HIGH,
    status=TaskStatus.QUEUED
)

# Agent model - Tracks agent performance
agent = Agent(
    agent_id="default",
    tasks_completed=150,
    success_rate=0.92,
    patterns_learned=25
)

# Metric model - Time-series metrics
metric = Metric(
    metric_name="task_duration",
    metric_value=45.2,
    metric_type="histogram",
    agent_id="default"
)
```

### Repository Pattern

Clean, async repository pattern for database operations:

```python
from database.repository import TaskRepository, AgentRepository

# Create a task
task = await TaskRepository.create(
    db,
    {
        "task_id": "abc123",
        "prompt": "Build a web scraper",
        "priority": "high"
    }
)

# Update task status
await TaskRepository.update_status(
    db,
    "abc123",
    TaskStatus.RUNNING,
    started_at=datetime.now()
)

# Get task statistics
stats = await TaskRepository.get_statistics(db, agent_id="default")
# Returns: {"total": 150, "by_status": {"completed": 138, "failed": 12}}
```

### Database Configuration

The system uses async SQLAlchemy with SQLite by default, but supports PostgreSQL and MySQL:

```python
# SQLite (default)
DATABASE_URL = "sqlite+aiosqlite:///./data/zenomind.db"

# PostgreSQL
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/zenomind"

# MySQL
DATABASE_URL = "mysql+aiomysql://user:pass@localhost/zenomind"
```

---

## Error Handling & Retry Logic

### Exponential Backoff

Automatic retry with exponential backoff for transient failures:

```python
from utils.retry import retry_async, RetryConfig, NETWORK_RETRY_CONFIG

@retry_async(NETWORK_RETRY_CONFIG)
async def fetch_data_from_api():
    # This will retry up to 5 times with exponential backoff
    response = await api_client.get("/data")
    return response

# Custom retry configuration
custom_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True  # Adds randomization to prevent thundering herd
)

@retry_async(custom_config)
async def custom_operation():
    # Your code here
    pass
```

### Circuit Breaker Pattern

Prevents cascading failures by stopping calls to failing services:

```python
from utils.retry import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0
)

async def call_external_service():
    return await breaker.call(make_api_request, url="https://api.example.com")
```

### Comprehensive Error Handler

Categorizes, logs, and attempts recovery from errors:

```python
from utils.error_handler import error_handler, ErrorCategory, handle_errors

# Automatic error handling with decorator
@handle_errors(category=ErrorCategory.NETWORK, reraise=True)
async def network_operation():
    # Your code here
    pass

# Manual error handling
try:
    await risky_operation()
except Exception as e:
    context = await error_handler.handle_error(
        e,
        function_name="risky_operation",
        metadata={"user_id": "123"},
        attempt_recovery=True
    )
    # Error is categorized, logged, and recovery attempted
```

### Error Categories

- **NETWORK**: Network-related errors
- **DATABASE**: Database errors
- **VALIDATION**: Input validation errors
- **AUTHENTICATION**: Auth errors
- **AUTHORIZATION**: Permission errors
- **RESOURCE**: Resource not found
- **RATE_LIMIT**: Rate limiting
- **TIMEOUT**: Timeout errors
- **INTERNAL**: Internal server errors
- **EXTERNAL_API**: Third-party API errors

### Severity Levels

- **LOW**: Minor issues, no immediate action needed
- **MEDIUM**: Issues that need attention
- **HIGH**: Critical issues requiring immediate attention
- **CRITICAL**: System-breaking issues

---

## Plugin System

### Overview

Dynamic plugin system for extending agent capabilities without modifying core code.

### Plugin Types

1. **Tool Plugins**: Provide executable tools/functions
2. **Data Source Plugins**: Access to external data
3. **Integration Plugins**: Third-party service integrations

### Creating a Plugin

```python
from plugins.base import ToolPlugin, PluginMetadata, PluginCapability

class MyCustomPlugin(ToolPlugin):
    """Custom tool plugin"""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="my_custom_tool",
            name="My Custom Tool",
            version="1.0.0",
            description="Does something useful",
            capabilities=[PluginCapability.TOOL],
            config_schema={
                "api_key": {"type": "string", "required": True}
            }
        )

    async def initialize(self) -> bool:
        self.metadata = self.get_metadata()
        self.initialized = True
        return True

    async def shutdown(self):
        self.initialized = False

    async def execute(self, param1: str, param2: int) -> dict:
        # Your tool logic here
        return {"result": f"Processed {param1} with {param2}"}

    def get_tool_schema(self) -> dict:
        return {
            "name": "my_custom_tool",
            "description": "My custom tool",
            "parameters": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"}
            }
        }
```

### Plugin Management

```python
from plugins.manager import plugin_manager
from plugins.loader import plugin_loader

# Discover plugins from directory
plugin_loader.discover_plugins()
plugin_loader.register_discovered_plugins()

# Load a plugin
await plugin_manager.load_plugin(MyCustomPlugin, config={"api_key": "xxx"})

# Enable/disable plugin
await plugin_manager.enable_plugin("my_custom_tool")
await plugin_manager.disable_plugin("my_custom_tool")

# Get all enabled plugins
enabled = plugin_manager.get_enabled_plugins()

# Health check
health = await plugin_manager.health_check_all()
```

### Built-in Plugins

#### Calculator Plugin
Basic arithmetic calculator:

```python
from plugins.base import CalculatorPlugin

plugin = CalculatorPlugin()
await plugin.initialize()

result = await plugin.execute("+", 5, 3)  # Returns 8
```

#### Weather Plugin
Weather data integration (example):

```python
from plugins.builtins.weather_plugin import WeatherPlugin

plugin = WeatherPlugin(config={"api_key": "your_key"})
await plugin.initialize()
await plugin.connect()

weather = await plugin.get_current_weather("San Francisco")
# Returns: {"location": "San Francisco", "temperature": 22.5, ...}
```

---

## Advanced Learning System

### Overview

Multi-component learning system that enables the agent to improve over time through pattern recognition, strategy optimization, and experience replay.

### Components

#### 1. Pattern Recognizer

Identifies common patterns in tasks:

```python
from learning.pattern_recognizer import PatternRecognizer

recognizer = PatternRecognizer()

# Analyze a task
patterns = await recognizer.analyze_task(
    task_prompt="Search for Python tutorials and create a summary",
    success=True,
    duration=45.2,
    tools_used=["search", "summarize"]
)
# Returns: ["pattern_search", "pattern_summarize"]

# Get recommendations
recs = await recognizer.get_recommendations(
    "Build a web scraper for news articles"
)
# Returns pattern-based suggestions
```

**Pattern Types**:
- Keyword patterns: search, create, analyze, transform, summarize, code, data
- Structural patterns: lists, comparisons, multi-step, questions

#### 2. Strategy Optimizer

Optimizes task execution strategies using multi-armed bandit (UCB):

```python
from learning.strategy_optimizer import StrategyOptimizer

optimizer = StrategyOptimizer(epsilon=0.1)

# Select optimal strategy for task
strategy = await optimizer.select_strategy(
    patterns=["search", "analyze"],
    context={"complexity": "high"}
)

# Update strategy performance
await optimizer.update_strategy_performance(
    strategy_id=strategy.strategy_id,
    success=True,
    duration=60.5,
    reward=0.85
)

# Get strategy rankings
rankings = optimizer.get_strategy_rankings()
# Returns strategies sorted by performance
```

**Built-in Strategies**:
- Direct Execution: Execute task directly
- Decompose and Execute: Break down into steps
- Research First: Research before executing
- Iterative Refinement: Draft, evaluate, refine

#### 3. Experience Replay

Stores and replays agent experiences:

```python
from learning.experience_replay import ExperienceReplay

replay = ExperienceReplay(max_size=10000)

# Add experience
experience = await replay.add_experience(
    task_prompt="Create a Python web server",
    task_result="Successfully created Flask server",
    success=True,
    duration=120.0,
    patterns=["create", "code"],
    tools_used=["python", "web"]
)

# Sample batch for learning
batch = await replay.sample_batch(batch_size=32, prioritized=True)

# Get successful experiences
successes = await replay.get_successful_experiences(
    patterns=["code"],
    limit=10
)
```

**Features**:
- Prioritized sampling (higher priority for failures and rare patterns)
- Automatic reward calculation
- Experience deduplication
- Batch retrieval for learning

#### 4. Learning Engine

Integrates all learning components:

```python
from learning.learning_engine import learning_engine

# Process completed task for learning
await learning_engine.process_task_completion(
    task_prompt="Research AI trends",
    task_result="Completed analysis",
    success=True,
    duration=180.0,
    tools_used=["search", "analyze"],
    strategy_id="research_first"
)

# Get recommendations for new task
recs = await learning_engine.get_task_recommendations(
    "Analyze financial data and create report"
)
# Returns: patterns, recommended strategy, similar successes, confidence

# Get learning insights
insights = await learning_engine.get_learning_insights()
# Returns comprehensive learning statistics

# Export learned knowledge
knowledge = await learning_engine.export_knowledge()
# Save for later import
```

---

## Enhanced Consciousness Streaming

### Overview

Real-time streaming of agent thoughts, emotions, and insights with rich contextual information.

### Event Types

1. **Thought**: Agent reasoning and planning
2. **Action**: Tool calls and executions
3. **Observation**: Results and feedback
4. **Reflection**: Self-assessment and meta-cognition
5. **Emotion**: Agent emotional states
6. **Progress**: Task progress updates
7. **Insight**: Discoveries and insights

### Emotional States

The system tracks 15+ emotion types:

**Positive States**:
- Curious: Exploring new information
- Focused: Deep in work
- Confident: High certainty
- Satisfied: Task completed well
- Excited: Discovered something interesting
- Determined: Pushing through challenges

**Neutral States**:
- Analyzing: Processing information
- Planning: Strategizing approach
- Searching: Looking for information
- Reflecting: Thinking about approach

**Challenging States**:
- Uncertain: Low confidence
- Stuck: Can't make progress
- Confused: Don't understand
- Frustrated: Hitting obstacles
- Tired: Resource constrained

**Meta States**:
- Learning: Acquiring new knowledge
- Adapting: Changing approach

### Usage

```python
from websocket.consciousness import ConsciousnessStreamer
from websocket.emotional_state import emotional_state_tracker, EmotionType

streamer = ConsciousnessStreamer()

# Emit thought
await streamer.emit_thought(
    agent_id="default",
    task_id="task123",
    thought="I should break this problem down into smaller steps",
    thought_type="planning"
)

# Emit emotion with context
await streamer.emit_emotion(
    agent_id="default",
    task_id="task123",
    emotion="curious",
    intensity=0.8,
    reason="Found interesting pattern in the data"
)

# Emit progress update
await streamer.emit_progress(
    agent_id="default",
    task_id="task123",
    progress=0.6,
    step_description="Analyzing results from API"
)

# Emit insight
await streamer.emit_insight(
    agent_id="default",
    task_id="task123",
    insight="The data shows a strong correlation between X and Y",
    confidence=0.85
)

# Track emotional states
emotional_state_tracker.update_state(
    emotion=EmotionType.FOCUSED,
    intensity=0.9,
    reason="Deep into complex analysis"
)

# Get emotional insights
insights = emotional_state_tracker.get_emotion_insights()
# Returns: most common emotions, average intensity, patterns
```

---

## Metrics & Analytics

### Overview

Comprehensive metrics collection and analytics for monitoring agent performance.

### Metric Collection

```python
from database.repository import MetricRepository

# Record a metric
await MetricRepository.record(
    db,
    metric_name="task_duration",
    metric_value=45.2,
    metric_type="histogram",
    agent_id="default",
    task_id="task123",
    labels={"task_type": "research", "priority": "high"}
)

# Get time series data
metrics = await MetricRepository.get_time_series(
    db,
    metric_name="task_duration",
    agent_id="default",
    start_time=datetime.now() - timedelta(days=7),
    limit=1000
)

# Get aggregated value
avg_duration = await MetricRepository.get_aggregated(
    db,
    metric_name="task_duration",
    aggregation="avg",
    agent_id="default"
)
```

### Agent Metrics

```python
from database.repository import AgentRepository

# Update agent metrics
await AgentRepository.update_metrics(
    db,
    agent_id="default",
    tasks_completed=150,
    patterns_learned=25,
    success_rate=0.92
)

# Increment task count
await AgentRepository.increment_task_count(
    db,
    agent_id="default",
    success=True,
    duration=45.2
)
# Automatically updates success rate and average duration
```

### Task Statistics

```python
from database.repository import TaskRepository

# Get comprehensive statistics
stats = await TaskRepository.get_statistics(db, agent_id="default")
# Returns:
# {
#     "total": 150,
#     "by_status": {
#         "completed": 138,
#         "failed": 10,
#         "running": 2
#     }
# }
```

---

## API Reference

### Task Management

#### Create Task
```http
POST /api/tasks
Content-Type: application/json

{
  "prompt": "Research AI papers from 2024",
  "priority": "high",
  "max_duration": 3600,
  "enable_browser": true,
  "enable_learning": true
}
```

Response:
```json
{
  "task_id": "abc123",
  "status": "queued",
  "created_at": "2025-11-18T10:30:00Z",
  "message": "Task queued successfully"
}
```

#### Get Task Status
```http
GET /api/tasks/{task_id}
```

Response:
```json
{
  "task_id": "abc123",
  "status": "completed",
  "progress": 1.0,
  "result": "Found 5 relevant papers...",
  "created_at": "2025-11-18T10:30:00Z",
  "completed_at": "2025-11-18T10:35:00Z"
}
```

#### List Tasks
```http
GET /api/tasks?status=completed&limit=50
```

#### Cancel Task
```http
DELETE /api/tasks/{task_id}
```

### Agent Management

#### List Agents
```http
GET /api/agents
```

Response:
```json
{
  "agents": [
    {
      "agent_id": "default",
      "name": "Default Ambient Agent",
      "status": "ready",
      "tasks_completed": 150,
      "success_rate": 0.92,
      "patterns_learned": 25
    }
  ]
}
```

#### Get Agent Details
```http
GET /api/agents/{agent_id}
```

### Metrics

#### Task Statistics
```http
GET /api/metrics/tasks?agent_id=default
```

Response:
```json
{
  "total": 150,
  "by_status": {
    "completed": 138,
    "failed": 10,
    "running": 2
  }
}
```

#### Time Series Metrics
```http
GET /api/metrics/time-series/task_duration?agent_id=default&limit=100
```

#### Aggregated Metrics
```http
GET /api/metrics/aggregate/task_duration?aggregation=avg&agent_id=default
```

Response:
```json
{
  "metric_name": "task_duration",
  "aggregation": "avg",
  "value": 45.2
}
```

### Memory

#### Search Memory
```http
GET /api/memory/search?query=python&limit=10
```

#### Recent Memories
```http
GET /api/memory/recent?limit=20
```

---

## Performance Considerations

### Database Optimization

- **Indexes**: Multi-column indexes on frequently queried fields
- **Connection Pooling**: Async connection pool for better concurrency
- **Query Optimization**: Repository pattern with optimized queries
- **Lazy Loading**: Relationships loaded only when needed

### Caching Strategy

- **In-Memory Cache**: Task cache for quick access
- **Database Fallback**: Cache misses fall back to database
- **Cache Invalidation**: Automatic invalidation on updates

### Scalability

- **Async/Await**: Non-blocking I/O throughout
- **Horizontal Scaling**: Stateless design allows multiple instances
- **Database Sharding**: Ready for sharding on agent_id or task_id
- **Metrics Cleanup**: Automatic cleanup of old metrics

---

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./data/zenomind.db

# API Keys
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# Redis (for task queue)
REDIS_URL=redis://localhost:6379

# Memory
MEMORY_PERSIST_DIR=./data/memory
```

### Config File

See `backend/config.toml` for detailed configuration options.

---

## Monitoring & Debugging

### Logging

All components use structured logging with loguru:

```python
from loguru import logger

logger.info("Task completed", task_id="abc123", duration=45.2)
logger.error("Task failed", task_id="abc123", error="Connection timeout")
```

### Health Checks

```http
GET /
```

Returns system health including:
- Service status
- Active agents count
- Active tasks count
- Timestamp

---

## Future Enhancements

Potential areas for expansion:

1. **Multi-Agent Orchestration**: Coordinate multiple specialized agents
2. **Advanced Visualization**: Rich dashboards for metrics and patterns
3. **Voice Interface**: Audio input/output for tasks
4. **Collaborative Features**: Multi-user task management
5. **Advanced Security**: Authentication, authorization, audit logs
6. **Cloud Deployment**: Kubernetes manifests, cloud-native features
7. **CLI Interface**: Command-line tool for agent management

---

## Support & Contributing

For issues, questions, or contributions, please see the main README.md file.

---

**Built with ❤️ by the ZenoMind Team**

_Last Updated: November 18, 2025_
