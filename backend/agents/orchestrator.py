"""
Multi-Agent Orchestrator - Coordinate specialized agents for complex goals
Signature Feature: Intelligent agent selection and task decomposition
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "openmanus-source"))

import asyncio
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
from loguru import logger
from enum import Enum

from agents.ambient import AmbientAgent
from agents.browser import EnhancedBrowserAgent
from memory.vector_store import MemoryStore
from websocket.consciousness import ConsciousnessStreamer


class AgentRole(Enum):
    """Specialized agent roles"""
    RESEARCHER = "researcher"  # Information gathering and research
    ANALYST = "analyst"  # Data analysis and insights
    CODER = "coder"  # Code writing and debugging
    BROWSER = "browser"  # Web browsing and interaction
    WRITER = "writer"  # Content creation
    COORDINATOR = "coordinator"  # Task coordination


class TaskComplexity(Enum):
    """Task complexity levels"""
    SIMPLE = "simple"  # Single agent, single step
    MODERATE = "moderate"  # Single agent, multiple steps
    COMPLEX = "complex"  # Multiple agents, coordinated
    EXPERT = "expert"  # Multiple agents, sequential/parallel


class AgentOrchestrator:
    """
    Multi-Agent Orchestrator for complex task execution

    Features:
    - Intelligent task decomposition
    - Agent role specialization
    - Parallel and sequential execution
    - Result aggregation
    - Dynamic agent allocation
    - Inter-agent communication
    """

    def __init__(
        self,
        memory_store: MemoryStore,
        consciousness_streamer: ConsciousnessStreamer
    ):
        self.memory_store = memory_store
        self.consciousness_streamer = consciousness_streamer

        # Agent registry
        self.agents: Dict[str, AmbientAgent] = {}
        self.agent_specializations: Dict[str, AgentRole] = {}

        # Execution tracking
        self.active_orchestrations: Dict[str, Dict[str, Any]] = {}

        # Performance metrics
        self.orchestration_stats = {
            "total_orchestrations": 0,
            "successful_orchestrations": 0,
            "failed_orchestrations": 0,
            "average_agents_used": 0.0,
            "total_agents_created": 0
        }

    async def create_specialized_agent(
        self,
        agent_id: str,
        role: AgentRole,
        capabilities: Optional[List[str]] = None
    ) -> AmbientAgent:
        """
        Create a specialized agent with specific role

        Args:
            agent_id: Unique agent identifier
            role: Agent role specialization
            capabilities: List of specific capabilities

        Returns:
            Created agent
        """
        agent = AmbientAgent(
            agent_id=agent_id,
            memory_store=self.memory_store,
            consciousness_streamer=self.consciousness_streamer
        )

        await agent.initialize()

        self.agents[agent_id] = agent
        self.agent_specializations[agent_id] = role

        logger.info(f"🤖 Created specialized {role.value} agent: {agent_id}")
        self.orchestration_stats["total_agents_created"] += 1

        return agent

    async def decompose_task(
        self,
        prompt: str,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Analyze and decompose a complex task into subtasks

        Args:
            prompt: Original task prompt
            task_id: Task identifier

        Returns:
            Task decomposition plan
        """
        await self.consciousness_streamer.emit_thought(
            agent_id="orchestrator",
            task_id=task_id,
            thought="Analyzing task complexity and decomposing into subtasks",
            thought_type="planning"
        )

        # Analyze task complexity (simplified heuristics)
        complexity = self._assess_complexity(prompt)

        # Determine required agent roles
        required_roles = self._determine_required_roles(prompt)

        # Create subtask plan
        subtasks = self._create_subtasks(prompt, required_roles, complexity)

        plan = {
            "task_id": task_id,
            "original_prompt": prompt,
            "complexity": complexity.value,
            "required_roles": [role.value for role in required_roles],
            "subtasks": subtasks,
            "execution_strategy": self._determine_execution_strategy(complexity),
            "created_at": datetime.now()
        }

        await self.consciousness_streamer.emit_thought(
            agent_id="orchestrator",
            task_id=task_id,
            thought=f"Task decomposed into {len(subtasks)} subtasks with {len(required_roles)} agent roles",
            thought_type="planning"
        )

        return plan

    def _assess_complexity(self, prompt: str) -> TaskComplexity:
        """Assess task complexity"""
        prompt_lower = prompt.lower()

        # Heuristic-based complexity assessment
        complexity_indicators = {
            "multiple": 1,
            "compare": 1,
            "analyze": 1,
            "research": 1,
            "then": 1,
            "after": 1,
            "while": 1,
            "coordinate": 2,
            "integrate": 2,
            "comprehensive": 2,
            "detailed": 1,
            "complex": 2
        }

        score = sum(
            complexity_indicators.get(word, 0)
            for word in prompt_lower.split()
            if word in complexity_indicators
        )

        # Word count also indicates complexity
        word_count = len(prompt.split())

        if score >= 5 or word_count > 50:
            return TaskComplexity.EXPERT
        elif score >= 3 or word_count > 30:
            return TaskComplexity.COMPLEX
        elif score >= 1 or word_count > 15:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.SIMPLE

    def _determine_required_roles(self, prompt: str) -> List[AgentRole]:
        """Determine which agent roles are needed"""
        prompt_lower = prompt.lower()
        roles = set()

        role_keywords = {
            AgentRole.RESEARCHER: ["research", "find", "search", "lookup", "investigate", "discover"],
            AgentRole.ANALYST: ["analyze", "compare", "evaluate", "assess", "examine", "study"],
            AgentRole.CODER: ["code", "program", "write", "implement", "debug", "script"],
            AgentRole.BROWSER: ["browse", "website", "web", "click", "navigate", "scrape"],
            AgentRole.WRITER: ["write", "create", "draft", "compose", "generate", "document"],
        }

        for role, keywords in role_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                roles.add(role)

        # Always include coordinator for multi-agent tasks
        if len(roles) > 1:
            roles.add(AgentRole.COORDINATOR)

        # Default to researcher if nothing specific detected
        if not roles:
            roles.add(AgentRole.RESEARCHER)

        return list(roles)

    def _create_subtasks(
        self,
        prompt: str,
        roles: List[AgentRole],
        complexity: TaskComplexity
    ) -> List[Dict[str, Any]]:
        """Create subtask breakdown"""
        subtasks = []

        if complexity == TaskComplexity.SIMPLE:
            # Single task
            subtasks.append({
                "subtask_id": "subtask_1",
                "description": prompt,
                "assigned_role": roles[0].value if roles else AgentRole.RESEARCHER.value,
                "dependencies": [],
                "priority": "high"
            })

        elif complexity == TaskComplexity.MODERATE:
            # Break into 2-3 steps
            subtasks.append({
                "subtask_id": "subtask_1",
                "description": f"Gather information for: {prompt}",
                "assigned_role": AgentRole.RESEARCHER.value,
                "dependencies": [],
                "priority": "high"
            })

            subtasks.append({
                "subtask_id": "subtask_2",
                "description": f"Process and complete: {prompt}",
                "assigned_role": roles[0].value if roles else AgentRole.ANALYST.value,
                "dependencies": ["subtask_1"],
                "priority": "high"
            })

        elif complexity in [TaskComplexity.COMPLEX, TaskComplexity.EXPERT]:
            # Multiple coordinated subtasks
            subtasks.append({
                "subtask_id": "subtask_1",
                "description": f"Research and gather data for: {prompt}",
                "assigned_role": AgentRole.RESEARCHER.value,
                "dependencies": [],
                "priority": "critical"
            })

            if AgentRole.BROWSER in roles:
                subtasks.append({
                    "subtask_id": "subtask_2",
                    "description": "Collect web-based information",
                    "assigned_role": AgentRole.BROWSER.value,
                    "dependencies": [],
                    "priority": "high"
                })

            subtasks.append({
                "subtask_id": "subtask_3",
                "description": f"Analyze collected information",
                "assigned_role": AgentRole.ANALYST.value,
                "dependencies": ["subtask_1"],
                "priority": "high"
            })

            subtasks.append({
                "subtask_id": "subtask_4",
                "description": f"Synthesize final result for: {prompt}",
                "assigned_role": AgentRole.WRITER.value,
                "dependencies": ["subtask_3"],
                "priority": "high"
            })

        return subtasks

    def _determine_execution_strategy(self, complexity: TaskComplexity) -> str:
        """Determine execution strategy"""
        if complexity == TaskComplexity.SIMPLE:
            return "sequential"
        elif complexity == TaskComplexity.MODERATE:
            return "sequential"
        elif complexity == TaskComplexity.COMPLEX:
            return "mixed"  # Some parallel, some sequential
        else:
            return "parallel_sequential"  # Parallel where possible, sequential where needed

    async def orchestrate(
        self,
        prompt: str,
        task_id: str,
        max_duration: int = 3600
    ) -> Dict[str, Any]:
        """
        Orchestrate multi-agent task execution

        Args:
            prompt: Task prompt
            task_id: Task identifier
            max_duration: Maximum execution time in seconds

        Returns:
            Orchestration result
        """
        start_time = datetime.now()

        await self.consciousness_streamer.emit_thought(
            agent_id="orchestrator",
            task_id=task_id,
            thought=f"Beginning orchestration for: {prompt}",
            thought_type="initiation"
        )

        self.orchestration_stats["total_orchestrations"] += 1

        try:
            # Step 1: Decompose task
            plan = await self.decompose_task(prompt, task_id)

            # Step 2: Allocate agents
            agent_assignments = await self._allocate_agents(plan, task_id)

            # Step 3: Execute plan
            results = await self._execute_plan(
                plan,
                agent_assignments,
                task_id,
                max_duration
            )

            # Step 4: Aggregate results
            final_result = await self._aggregate_results(
                results,
                plan,
                task_id
            )

            # Update stats
            self.orchestration_stats["successful_orchestrations"] += 1
            agents_used = len(agent_assignments)
            current_avg = self.orchestration_stats["average_agents_used"]
            total = self.orchestration_stats["total_orchestrations"]
            self.orchestration_stats["average_agents_used"] = (
                (current_avg * (total - 1) + agents_used) / total
            )

            elapsed = (datetime.now() - start_time).total_seconds()

            await self.consciousness_streamer.emit_thought(
                agent_id="orchestrator",
                task_id=task_id,
                thought=f"Orchestration completed successfully in {elapsed:.1f}s using {agents_used} agents",
                thought_type="completion"
            )

            return {
                "success": True,
                "result": final_result,
                "plan": plan,
                "agents_used": agents_used,
                "execution_time": elapsed,
                "subtask_results": results
            }

        except Exception as e:
            self.orchestration_stats["failed_orchestrations"] += 1

            logger.error(f"Orchestration failed for task {task_id}: {e}")

            await self.consciousness_streamer.emit_thought(
                agent_id="orchestrator",
                task_id=task_id,
                thought=f"Orchestration failed: {str(e)}",
                thought_type="error"
            )

            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }

    async def _allocate_agents(
        self,
        plan: Dict[str, Any],
        task_id: str
    ) -> Dict[str, str]:
        """
        Allocate agents to subtasks

        Returns:
            Mapping of subtask_id to agent_id
        """
        assignments = {}

        for subtask in plan["subtasks"]:
            role = AgentRole(subtask["assigned_role"])

            # Find or create agent for this role
            agent_id = await self._get_or_create_agent(role, task_id)

            assignments[subtask["subtask_id"]] = agent_id

        return assignments

    async def _get_or_create_agent(
        self,
        role: AgentRole,
        task_id: str
    ) -> str:
        """Get existing agent or create new one"""
        # Try to find existing agent with this role
        for agent_id, agent_role in self.agent_specializations.items():
            if agent_role == role and self.agents[agent_id].status == "ready":
                return agent_id

        # Create new agent
        agent_id = f"{role.value}_{task_id}_{len(self.agents)}"
        await self.create_specialized_agent(agent_id, role)

        return agent_id

    async def _execute_plan(
        self,
        plan: Dict[str, Any],
        assignments: Dict[str, str],
        task_id: str,
        max_duration: int
    ) -> Dict[str, Any]:
        """Execute the task plan"""
        results = {}
        completed_subtasks = set()

        strategy = plan["execution_strategy"]

        if strategy == "sequential":
            # Execute subtasks sequentially
            for subtask in plan["subtasks"]:
                result = await self._execute_subtask(
                    subtask,
                    assignments,
                    task_id,
                    completed_subtasks
                )
                results[subtask["subtask_id"]] = result
                completed_subtasks.add(subtask["subtask_id"])

        elif strategy == "parallel_sequential":
            # Group by dependency level and execute in waves
            dependency_levels = self._build_dependency_levels(plan["subtasks"])

            for level, subtasks in enumerate(dependency_levels):
                # Execute this level in parallel
                tasks = [
                    self._execute_subtask(subtask, assignments, task_id, completed_subtasks)
                    for subtask in subtasks
                ]

                level_results = await asyncio.gather(*tasks, return_exceptions=True)

                for subtask, result in zip(subtasks, level_results):
                    results[subtask["subtask_id"]] = result
                    completed_subtasks.add(subtask["subtask_id"])

        else:  # mixed or default
            # Simple sequential for now
            for subtask in plan["subtasks"]:
                result = await self._execute_subtask(
                    subtask,
                    assignments,
                    task_id,
                    completed_subtasks
                )
                results[subtask["subtask_id"]] = result
                completed_subtasks.add(subtask["subtask_id"])

        return results

    def _build_dependency_levels(self, subtasks: List[Dict]) -> List[List[Dict]]:
        """Build dependency levels for parallel execution"""
        levels = []
        remaining = subtasks.copy()
        completed = set()

        while remaining:
            # Find subtasks with no incomplete dependencies
            current_level = []

            for subtask in remaining:
                dependencies = subtask.get("dependencies", [])
                if all(dep in completed for dep in dependencies):
                    current_level.append(subtask)

            if not current_level:
                # Circular dependency or error
                logger.warning("Circular dependency detected, adding remaining tasks")
                current_level = remaining.copy()

            levels.append(current_level)

            for subtask in current_level:
                completed.add(subtask["subtask_id"])
                remaining.remove(subtask)

        return levels

    async def _execute_subtask(
        self,
        subtask: Dict[str, Any],
        assignments: Dict[str, str],
        task_id: str,
        completed_subtasks: set
    ) -> Any:
        """Execute a single subtask"""
        subtask_id = subtask["subtask_id"]
        agent_id = assignments[subtask_id]

        # Check dependencies
        dependencies = subtask.get("dependencies", [])
        for dep in dependencies:
            if dep not in completed_subtasks:
                raise Exception(f"Dependency {dep} not completed for {subtask_id}")

        agent = self.agents[agent_id]

        await self.consciousness_streamer.emit_thought(
            agent_id="orchestrator",
            task_id=task_id,
            thought=f"Executing subtask {subtask_id} with {agent_id}",
            thought_type="action"
        )

        # Execute subtask
        result = await agent.execute_task(
            prompt=subtask["description"],
            task_id=f"{task_id}_{subtask_id}",
            max_duration=600,  # 10 minutes per subtask
            enable_browser=True
        )

        return result

    async def _aggregate_results(
        self,
        results: Dict[str, Any],
        plan: Dict[str, Any],
        task_id: str
    ) -> str:
        """Aggregate results from all subtasks"""
        await self.consciousness_streamer.emit_thought(
            agent_id="orchestrator",
            task_id=task_id,
            thought="Aggregating results from all subtasks",
            thought_type="reflection"
        )

        # Simple aggregation: concatenate results
        aggregated = f"Task: {plan['original_prompt']}\n\n"
        aggregated += f"Complexity: {plan['complexity']}\n"
        aggregated += f"Subtasks completed: {len(results)}\n\n"

        for subtask_id, result in results.items():
            subtask = next(
                (st for st in plan["subtasks"] if st["subtask_id"] == subtask_id),
                None
            )
            if subtask:
                aggregated += f"\n### {subtask['description']}\n"
                aggregated += f"{result}\n"

        return aggregated

    async def cleanup_agents(self):
        """Cleanup all managed agents"""
        logger.info("🧹 Cleaning up orchestrator agents...")

        for agent in self.agents.values():
            await agent.cleanup()

        self.agents.clear()
        self.agent_specializations.clear()

        logger.info("✅ Orchestrator cleanup complete")

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestration statistics"""
        return {
            **self.orchestration_stats,
            "active_agents": len(self.agents),
            "active_orchestrations": len(self.active_orchestrations)
        }
