"""
Chat Service

Manages conversational interactions with agents, supporting commands,
context management, and streaming responses.
"""

import uuid
import asyncio
from typing import Dict, Any, Optional, List, AsyncIterator
from datetime import datetime
from enum import Enum

from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.agent_registry import AgentRegistry, AgentCapability
from src.agents.implementation_agent import ImplementationAgent
from src.agents.testing_agent import TestingAgent
from src.agents.documentation_agent import DocumentationAgent
from src.observability import StructuredLogger


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message:
    """Chat message model."""

    def __init__(
        self,
        content: str,
        role: MessageRole = MessageRole.USER,
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.message_id = message_id or str(uuid.uuid4())
        self.content = content
        self.role = role
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "content": self.content,
            "role": self.role.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class Conversation:
    """Conversation container with message history."""

    def __init__(
        self,
        conversation_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ):
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.messages: List[Message] = []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_message(self, message: Message) -> None:
        """Add message to conversation."""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history."""
        messages = self.messages[-limit:] if limit else self.messages
        return [msg.to_dict() for msg in messages]

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "messages": self.get_history(),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ChatCommand:
    """Chat command parser and executor."""

    COMMANDS = {
        "/orchestrate": "Orchestrate multi-agent workflow",
        "/masterplan": "Generate complete MasterPlan (Discovery + 50-task plan)",
        "/analyze": "Analyze project or code",
        "/test": "Run tests",
        "/help": "Show available commands",
        "/clear": "Clear conversation history",
        "/workspace": "Show current workspace info",
    }

    @classmethod
    def is_command(cls, message: str) -> bool:
        """Check if message is a command."""
        return message.strip().startswith("/")

    @classmethod
    def parse_command(cls, message: str) -> tuple[str, str]:
        """
        Parse command and arguments.

        Returns:
            tuple: (command, args)
        """
        parts = message.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        return command, args

    @classmethod
    def get_help(cls) -> str:
        """Get help text for all commands."""
        lines = ["Available commands:"]
        for cmd, desc in cls.COMMANDS.items():
            lines.append(f"  {cmd}: {desc}")
        return "\n".join(lines)


class ChatService:
    """
    Chat service for conversational agent interaction.

    Manages conversations, message history, command execution,
    and streaming responses from agents.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        metrics_collector=None,
        websocket_manager=None,
        sqlalchemy_session=None
    ):
        """
        Initialize chat service.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
            metrics_collector: MetricsCollector instance for LLM metrics (optional)
            websocket_manager: WebSocketManager instance for real-time progress (optional)
            sqlalchemy_session: SQLAlchemy database session for MGE V2 (optional)
        """
        from src.llm.anthropic_client import AnthropicClient
        from src.state.postgres_manager import PostgresManager

        self.logger = StructuredLogger("chat_service")
        self.conversations: Dict[str, Conversation] = {}
        self.registry = AgentRegistry()
        self.progress_callback = None  # Will be set per-request for WebSocket streaming
        self.metrics_collector = metrics_collector
        self.websocket_manager = websocket_manager

        # Initialize PostgreSQL for conversation persistence (state manager)
        try:
            self.db = PostgresManager()
            self.logger.info("PostgreSQL connection established for chat persistence")
        except Exception as e:
            self.logger.warning(f"Failed to connect to PostgreSQL: {e}. Conversations will not be persisted.")
            self.db = None

        # SQLAlchemy session for MGE V2 (if provided)
        self.sqlalchemy_session = sqlalchemy_session

        # Register specialized agents
        self._register_agents()

        # Orchestrator will be created per-request to use specific progress callback
        self.api_key = api_key

        # Create shared LLM client for conversational mode
        self.llm = AnthropicClient(api_key=api_key, metrics_collector=metrics_collector)

    def _register_agents(self):
        """Register all specialized agents in the registry."""
        # Implementation Agent
        self.registry.register(
            name="ImplementationAgent",
            agent_class=ImplementationAgent,
            capabilities={
                AgentCapability.CODE_GENERATION,
                AgentCapability.API_DESIGN,
                AgentCapability.REFACTORING
            },
            priority=10,
            description="Python code generation and implementation"
        )

        # Testing Agent
        self.registry.register(
            name="TestingAgent",
            agent_class=TestingAgent,
            capabilities={
                AgentCapability.UNIT_TESTING,
                AgentCapability.INTEGRATION_TESTING
            },
            priority=8,
            description="Test generation and execution"
        )

        # Documentation Agent
        self.registry.register(
            name="DocumentationAgent",
            agent_class=DocumentationAgent,
            capabilities={
                AgentCapability.API_DOCUMENTATION,
                AgentCapability.CODE_DOCUMENTATION,
                AgentCapability.USER_DOCUMENTATION
            },
            priority=6,
            description="Documentation generation"
        )

    def create_conversation(
        self,
        workspace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Create new conversation.

        Args:
            workspace_id: Associated workspace ID
            metadata: Additional conversation metadata
            session_id: WebSocket session ID for persistence
            user_id: Authenticated user ID from JWT token

        Returns:
            Conversation ID
        """
        conversation = Conversation(
            workspace_id=workspace_id,
            metadata=metadata,
            user_id=user_id,
        )
        self.conversations[conversation.conversation_id] = conversation

        # Persist to database with authenticated user_id
        if self.db and session_id:
            try:
                self.db.create_conversation(
                    conversation_id=conversation.conversation_id,
                    session_id=session_id,
                    metadata=metadata or {},
                    user_id=user_id
                )
                self.logger.info(f"Conversation {conversation.conversation_id} persisted to database with user {user_id}")
            except Exception as e:
                self.logger.error(f"Failed to persist conversation: {e}")

        self.logger.info(
            f"Created conversation {conversation.conversation_id}",
            extra={"workspace_id": workspace_id}
        )

        return conversation.conversation_id

    def update_conversation_metadata(
        self,
        conversation_id: str,
        metadata: Dict[str, Any]
    ):
        """
        Update conversation metadata (e.g., updating SID on reconnection).

        Args:
            conversation_id: Conversation ID
            metadata: Updated metadata dictionary
        """
        # Update in-memory conversation
        conversation = self.conversations.get(conversation_id)
        if conversation:
            conversation.metadata = metadata

        # Persist to database
        if self.db:
            try:
                self.db.update_conversation_metadata(
                    conversation_id=conversation_id,
                    metadata=metadata
                )
                self.logger.debug(f"Updated metadata for conversation {conversation_id}")
            except Exception as e:
                self.logger.error(f"Failed to update conversation metadata: {e}")

    def _save_message_to_db(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save a message to the database."""
        if self.db:
            try:
                self.db.save_message(
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                    metadata=metadata or {}
                )
            except Exception as e:
                self.logger.error(f"Failed to save message to database: {e}")

    def load_conversation_from_db(self, conversation_id: str) -> Optional[Conversation]:
        """
        Load conversation history from database.

        Args:
            conversation_id: Conversation ID to load

        Returns:
            Conversation object with loaded history, or None if not found
        """
        if not self.db:
            return None

        try:
            # Load conversation metadata
            conv_data = self.db.get_conversation(conversation_id)
            if not conv_data:
                return None

            # Create conversation object with user_id from database
            conversation = Conversation(
                conversation_id=conversation_id,
                workspace_id=conv_data.get('metadata', {}).get('workspace_id'),
                metadata=conv_data.get('metadata', {}),
                user_id=conv_data.get('user_id')
            )

            # Load messages
            messages_data = self.db.get_conversation_messages(conversation_id)
            for msg_data in messages_data:
                message = Message(
                    content=msg_data['content'],
                    role=MessageRole(msg_data['role']),
                    metadata=msg_data.get('metadata', {})
                )
                conversation.add_message(message)

            # Add to in-memory cache
            self.conversations[conversation_id] = conversation

            self.logger.info(f"Loaded conversation {conversation_id} from database with {len(messages_data)} messages")
            return conversation

        except Exception as e:
            self.logger.error(f"Failed to load conversation from database: {e}")
            return None

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID, loading from database if not in memory.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation object or None if not found
        """
        # Try in-memory first
        conversation = self.conversations.get(conversation_id)
        if conversation:
            return conversation

        # Try loading from database
        return self.load_conversation_from_db(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation.

        Returns:
            True if deleted, False if not found
        """
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            self.logger.info(f"Deleted conversation {conversation_id}")
            return True
        return False

    def list_conversations(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all conversations, optionally filtered by workspace.

        Args:
            workspace_id: Filter by workspace ID

        Returns:
            List of conversation dictionaries
        """
        conversations = self.conversations.values()

        if workspace_id:
            conversations = [c for c in conversations if c.workspace_id == workspace_id]

        return [c.to_dict() for c in conversations]

    async def send_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send message and get streaming response.

        Args:
            conversation_id: Conversation ID
            content: User message content
            metadata: Additional message metadata

        Yields:
            Response chunks with role, content, and metadata

        Raises:
            ValueError: If conversation not found
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Add user message
        user_message = Message(
            content=content,
            role=MessageRole.USER,
            metadata=metadata,
        )
        conversation.add_message(user_message)

        # Save user message to database
        self._save_message_to_db(
            conversation_id=conversation_id,
            role=MessageRole.USER.value,
            content=content,
            metadata=metadata
        )

        self.logger.info(
            f"Processing message in conversation {conversation_id}",
            extra={"message_length": len(content)}
        )

        # Check if message is a command
        if ChatCommand.is_command(content):
            async for chunk in self._handle_command(conversation, content, metadata):
                yield chunk
        else:
            async for chunk in self._handle_regular_message(conversation, content):
                yield chunk

    async def _handle_command(
        self,
        conversation: Conversation,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Handle command execution."""
        command, args = ChatCommand.parse_command(message)

        if command == "/help":
            response = ChatCommand.get_help()
            yield {
                "type": "message",
                "role": MessageRole.SYSTEM.value,
                "content": response,
                "done": True,
            }

            system_message = Message(
                content=response,
                role=MessageRole.SYSTEM,
            )
            conversation.add_message(system_message)

            # Save to database
            self._save_message_to_db(
                conversation_id=conversation.conversation_id,
                role=MessageRole.SYSTEM.value,
                content=response
            )

        elif command == "/clear":
            conversation.messages.clear()
            yield {
                "type": "message",
                "role": MessageRole.SYSTEM.value,
                "content": "Conversation cleared.",
                "done": True,
            }

        elif command == "/workspace":
            workspace_info = {
                "workspace_id": conversation.workspace_id,
                "conversation_id": conversation.conversation_id,
                "message_count": len(conversation.messages),
            }
            response = f"Workspace Info:\n```json\n{workspace_info}\n```"
            yield {
                "type": "message",
                "role": MessageRole.SYSTEM.value,
                "content": response,
                "done": True,
            }

        elif command == "/orchestrate":
            if not args:
                yield {
                    "type": "error",
                    "content": "Usage: /orchestrate <project description>",
                    "done": True,
                }
                return

            # Execute orchestration
            async for chunk in self._execute_orchestration(conversation, args):
                yield chunk

        elif command == "/masterplan":
            if not args:
                yield {
                    "type": "error",
                    "content": "Usage: /masterplan <project description>",
                    "done": True,
                }
                return

            # Execute MasterPlan generation
            async for chunk in self._execute_masterplan_generation(conversation, args, metadata):
                yield chunk

        else:
            yield {
                "type": "error",
                "content": f"Unknown command: {command}. Type /help for available commands.",
                "done": True,
            }

    async def _handle_regular_message(
        self,
        conversation: Conversation,
        message: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Handle regular conversation message."""
        # Detect if this is a direct implementation request or a discussion
        message_lower = message.lower().strip()

        # Keywords that indicate the user wants immediate implementation
        implementation_keywords = ['crear', 'create', 'generar', 'generate', 'implementar', 'implement',
                                  'hacer', 'make', 'escribir', 'write', 'code', 'coder', 'programa',
                                  'desarrollar', 'develop', 'armar', 'build']

        # Keywords indicating user gave enough context and is ready
        ready_keywords = ['si a todo', 'yes to all', 'dale arran', 'empecemos', "let's start",
                         'vamos', "let's go", 'dale', 'ok listo']

        # Keywords for planning/discussion (when user is asking questions)
        discussion_keywords = ['diseñar', 'design', 'planear', 'plan', 'pensar', 'think',
                              'podria', 'podría', 'como', 'cómo', 'que te parece', 'qué te parece']

        # Check conversation history - if user already gave detailed specs, they're ready
        recent_messages = conversation.get_history(limit=5)
        user_gave_details = len([m for m in recent_messages if m['role'] == 'user']) >= 3

        # Check message length - detailed messages with tech specs = ready
        word_count = len(message.split())
        has_tech_details = any(tech in message_lower for tech in
                              ['api', 'backend', 'frontend', 'database', 'db', 'fastapi', 'django',
                               'react', 'vue', 'angular', 'postgres', 'mongodb', 'redis', 'sprint',
                               'kanban', 'jira', 'git', 'docker', 'kubernetes'])

        is_detailed_request = word_count > 30 and has_tech_details

        # Check if it's a direct implementation request or user is ready
        is_direct_implementation = (
            (any(keyword in message_lower for keyword in implementation_keywords) and
             not any(keyword in message_lower for keyword in discussion_keywords)) or
            any(keyword in message_lower for keyword in ready_keywords) or
            is_detailed_request or
            (user_gave_details and word_count > 20)  # After 3+ messages with detail, assume ready
        )

        if is_direct_implementation:
            # Direct implementation - go straight to orchestration
            async for chunk in self._execute_orchestration(conversation, message):
                yield chunk
        else:
            # Conversational mode - discuss and help user refine the idea
            async for chunk in self._handle_conversational(conversation, message):
                yield chunk

    async def _handle_conversational(
        self,
        conversation: Conversation,
        message: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Handle conversational messages - greetings, questions, design discussions."""
        try:
            # Use LLM for friendly conversation
            loop = asyncio.get_event_loop()

            # Get conversation history for context
            recent_messages = conversation.get_history(limit=10)
            history_context = "\n".join([
                f"{msg['role']}: {msg['content'][:200]}"  # Limit each message to 200 chars
                for msg in recent_messages[-5:]  # Last 5 messages
            ])

            system_prompt = """Sos un asistente de IA amigable y conversacional llamado DevMatrix, especializado en desarrollo de software.

Características:
- Hablás en español argentino de manera natural y relajada
- Sos útil y profesional pero no formal ni robótico
- Cuando el usuario te saluda, saludás de vuelta y le contás brevemente qué podés hacer
- Si el usuario quiere diseñar/planear algo, ayudalo a definir los requerimientos pero NO seas insistente
- Hacé máximo 2-3 preguntas de clarificación por respuesta, no más
- Si el usuario ya dio suficiente contexto (menciona tecnologías, features, roles, etc.), decile que ya tenés todo y que use "crear" o "implementar" para empezar
- Si te preguntan sobre tecnologías o arquitectura, dales tu opinión directamente
- Mantené las respuestas cortas (2-4 oraciones)
- Usá formato markdown solo cuando ayude a la claridad
- Si detectás que el usuario está listo (dio detalles técnicos, respondió a tus preguntas), no sigas preguntando - decile cómo activar la implementación

Tus capacidades:
- Conversar sobre diseño de software y arquitectura
- Ayudar a definir requerimientos (pero no seas pesado con las preguntas)
- Responder preguntas técnicas directamente
- Cuando el usuario esté listo, decile que use "crear X" o "implementar Y" para que orqueste

Ejemplos de interacción:
- Usuario: "podríamos diseñar una app de task manager con FastAPI?" → "¡Dale! Task manager con FastAPI suena bien. ¿Qué features principales necesitás? (autenticación, asignación de tareas, notificaciones, etc.)"
- Usuario: "necesito kanban, sprints, roles Dev/PO/Lead" → "Perfecto, ya tengo claro el scope. Cuando quieras arrancar con la implementación, decime 'crear task manager con FastAPI, kanban, sprints y roles' y lo orquesto."
- Usuario: "qué me recomendás para una API?" → "Depende del caso de uso. FastAPI es genial para APIs modernas y rápidas, Django REST si necesitás muchas features out-of-the-box, Flask si preferís minimalismo. ¿Qué tipo de proyecto es?"""

            user_prompt = f"""Conversación reciente:
{history_context}

Usuario: {message}

Respondé de manera natural, amigable y útil. Si es una pregunta de diseño o planificación, hacé preguntas para entender mejor lo que necesita."""

            response = await loop.run_in_executor(
                None,
                lambda: self.llm.generate(
                    messages=[{"role": "user", "content": user_prompt}],
                    system=system_prompt,
                    temperature=0.7,
                    max_tokens=400
                )
            )

            content = response['content']

            # Add assistant response to conversation
            assistant_message = Message(
                content=content,
                role=MessageRole.ASSISTANT,
            )
            conversation.add_message(assistant_message)

            # Save to database
            self._save_message_to_db(
                conversation_id=conversation.conversation_id,
                role=MessageRole.ASSISTANT.value,
                content=content
            )

            # Yield response
            yield {
                "type": "message",
                "role": MessageRole.ASSISTANT.value,
                "content": content,
                "done": True,
            }

        except Exception as e:
            error_message = f"Error en conversación: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            yield {
                "type": "error",
                "content": error_message,
                "done": True,
            }

    async def _execute_orchestration(
        self,
        conversation: Conversation,
        request: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute orchestration and stream progress.

        Uses MGE V2 pipeline if MGE_V2_ENABLED=true, otherwise uses legacy OrchestratorAgent.

        Yields:
            Progress updates and final result
        """
        from src.config.constants import MGE_V2_ENABLED

        if MGE_V2_ENABLED:
            # Use MGE V2 execution pipeline
            async for event in self._execute_mge_v2(conversation, request):
                yield event
        else:
            # Use legacy OrchestratorAgent (V1)
            async for event in self._execute_legacy_orchestration(conversation, request):
                yield event

    async def _execute_mge_v2(
        self,
        conversation: Conversation,
        request: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute MGE V2 pipeline and stream progress.

        Yields:
            Progress updates and final result
        """
        try:
            # Check if SQLAlchemy session is available
            if not self.sqlalchemy_session:
                yield {
                    "type": "error",
                    "content": "MGE V2 requires database session. Please initialize ChatService with sqlalchemy_session parameter.",
                    "done": True,
                }
                return

            # Import MGE V2 orchestration service
            from src.services.mge_v2_orchestration_service import MGE_V2_OrchestrationService
            from src.config.constants import MGE_V2_ENABLE_CACHING, MGE_V2_ENABLE_RAG

            # Initialize MGE V2 service
            mge_v2_service = MGE_V2_OrchestrationService(
                db=self.sqlalchemy_session,
                api_key=self.api_key,
                enable_caching=MGE_V2_ENABLE_CACHING,
                enable_rag=MGE_V2_ENABLE_RAG
            )

            # Send initial status
            yield {
                "type": "status",
                "content": "🚀 Iniciando MGE V2 pipeline...",
                "done": False,
            }

            # Stream MGE V2 pipeline events
            completion_event = None
            async for event in mge_v2_service.orchestrate_from_request(
                user_request=request,
                workspace_id=conversation.workspace_id,
                session_id=conversation.conversation_id,
                user_id=conversation.user_id
            ):
                # Translate MGE V2 events to chat service format
                event_type = event.get("type")

                if event_type == "status":
                    yield {
                        "type": "status",
                        "content": event.get("message", ""),
                        "done": False,
                    }
                elif event_type == "progress":
                    phase = event.get("phase", "")
                    message = event.get("message", "")
                    yield {
                        "type": "progress",
                        "event": phase,
                        "data": event,
                        "content": message,
                        "done": False,
                    }
                elif event_type == "complete":
                    completion_event = event
                elif event_type == "error":
                    yield {
                        "type": "error",
                        "content": event.get("message", "Unknown error"),
                        "done": True,
                    }
                    return

            # Format completion message
            if completion_event:
                response = self._format_mge_v2_completion(completion_event)

                # Add assistant response to conversation
                assistant_message = Message(
                    content=response,
                    role=MessageRole.ASSISTANT,
                    metadata={"mge_v2_result": completion_event},
                )
                conversation.add_message(assistant_message)

                # Save to database
                self._save_message_to_db(
                    conversation_id=conversation.conversation_id,
                    role=MessageRole.ASSISTANT.value,
                    content=response,
                    metadata={"mge_v2_result": completion_event}
                )

                # Yield final response
                yield {
                    "type": "message",
                    "role": MessageRole.ASSISTANT.value,
                    "content": response,
                    "metadata": completion_event,
                    "done": True,
                }

        except Exception as e:
            error_message = f"Error durante MGE V2 orchestration: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            yield {
                "type": "error",
                "content": error_message,
                "done": True,
            }

    def _format_mge_v2_completion(self, event: Dict[str, Any]) -> str:
        """Format MGE V2 completion event as markdown message."""
        lines = [
            "## ✅ MGE V2 Generation Complete",
            "",
            f"**MasterPlan ID**: `{event.get('masterplan_id', 'N/A')}`",
            f"**Total Tasks**: {event.get('total_tasks', 0)}",
            f"**Total Atoms**: {event.get('total_atoms', 0)}",
            f"**Precision**: {event.get('precision', 0) * 100:.1f}%",
            f"**Execution Time**: {event.get('execution_time', 0):.1f}s",
            "",
            "The code has been generated successfully using the MGE V2 pipeline. Check your workspace for the results.",
            "",
            "### Next Steps",
            "- Review the generated code",
            "- Run tests to validate functionality",
            "- Deploy to your environment",
        ]
        return "\n".join(lines)

    async def _execute_legacy_orchestration(
        self,
        conversation: Conversation,
        request: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute legacy orchestration (V1) and stream progress.

        Yields:
            Progress updates and final result
        """
        try:
            # Send initial status
            yield {
                "type": "status",
                "content": "Iniciando orquestación...",
                "done": False,
            }

            # Create a queue for progress events (using thread-safe queue)
            import queue
            progress_queue_sync = queue.Queue()

            # Create progress callback that puts events in queue
            def progress_callback(event_type: str, data: dict):
                """Callback to capture progress events from orchestrator."""
                try:
                    # Use thread-safe queue since this is called from thread pool
                    progress_queue_sync.put({
                        "event_type": event_type,
                        "data": data
                    })
                except Exception as e:
                    self.logger.error(f"Error in progress callback: {e}")

            # Create orchestrator with progress callback
            orchestrator = OrchestratorAgent(
                api_key=self.api_key,
                agent_registry=self.registry,
                progress_callback=progress_callback
            )

            # Execute orchestration in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            # Start orchestration task
            orchestration_task = loop.run_in_executor(
                None,
                orchestrator.orchestrate,
                request,
                conversation.workspace_id,
                None,
            )

            # Stream progress events while orchestration runs
            result = None
            orchestration_done = False

            while not orchestration_done:
                # Check for progress events (non-blocking)
                try:
                    event = progress_queue_sync.get(block=False)
                    yield {
                        "type": "progress",
                        "event": event["event_type"],
                        "data": event["data"],
                        "done": False,
                    }
                except:
                    # No progress events, check if orchestration is done
                    pass

                # Check if orchestration task is done
                if orchestration_task.done():
                    result = await orchestration_task
                    orchestration_done = True
                else:
                    # Small delay to avoid busy waiting
                    await asyncio.sleep(0.1)

            # Drain any remaining progress events
            while not progress_queue_sync.empty():
                try:
                    event = progress_queue_sync.get(block=False)
                    yield {
                        "type": "progress",
                        "event": event["event_type"],
                        "data": event["data"],
                        "done": False,
                    }
                except:
                    break

            # Format result as message
            response_lines = [
                f"## Orchestration Complete",
                f"",
                f"**Workspace**: `{result['workspace_id']}`",
                f"**Project Type**: {result['project_type']}",
                f"**Complexity**: {result['complexity']:.1f}",
                f"**Tasks**: {len(result['tasks'])}",
                f"",
                f"### Task Breakdown:",
            ]

            for task in result['tasks']:
                deps = f" (depends on: {', '.join(task['dependencies'])})" if task['dependencies'] else ""
                response_lines.append(
                    f"- **{task['id']}**: {task['description']}{deps}"
                )

            response = "\n".join(response_lines)

            # Add assistant response to conversation
            assistant_message = Message(
                content=response,
                role=MessageRole.ASSISTANT,
                metadata={"orchestration_result": result},
            )
            conversation.add_message(assistant_message)

            # Save to database
            self._save_message_to_db(
                conversation_id=conversation.conversation_id,
                role=MessageRole.ASSISTANT.value,
                content=response,
                metadata={"orchestration_result": result}
            )

            # Yield final response
            yield {
                "type": "message",
                "role": MessageRole.ASSISTANT.value,
                "content": response,
                "metadata": result,
                "done": True,
            }

        except Exception as e:
            error_message = f"Error during orchestration: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            yield {
                "type": "error",
                "content": error_message,
                "done": True,
            }

    async def _execute_masterplan_generation(
        self,
        conversation: Conversation,
        request: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute MasterPlan generation (Discovery + MasterPlan) with real-time progress.

        Args:
            conversation: The conversation context
            request: The user's project description
            metadata: Additional metadata including WebSocket sid

        Yields:
            Progress updates and final result
        """
        try:
            from src.services import DiscoveryAgent, MasterPlanGenerator

            # Get session_id - prefer current request metadata (with fresh sid), fallback to conversation metadata
            # This ensures discovery events are sent to the current WebSocket client
            session_id = (metadata or {}).get('sid') or conversation.metadata.get('sid', conversation.conversation_id)
            self.logger.info(f"📡 [_execute_masterplan_generation] Using session_id for discovery events", session_id=session_id, from_metadata=bool((metadata or {}).get('sid')))

            # Get user_id from conversation object (set by authenticated WebSocket connection)
            user_id = conversation.user_id
            if not user_id:
                raise ValueError("Conversation user_id not set - requires authenticated WebSocket connection")

            # Send initial status
            yield {
                "type": "status",
                "content": "🔍 Iniciando análisis DDD...",
                "done": False,
            }

            # Emit discovery_generation_start event to open modal on frontend
            await self.websocket_manager.emit_to_session(
                session_id=session_id,
                event="discovery_generation_start",
                data={"session_id": session_id}
            )

            # STEP 1: Discovery (with WebSocket progress)
            # WebSocket events will be emitted automatically by DiscoveryAgent
            discovery_agent = DiscoveryAgent(
                metrics_collector=self.metrics_collector,
                websocket_manager=self.websocket_manager
            )

            discovery_id = await discovery_agent.conduct_discovery(
                user_request=request,
                session_id=session_id,
                user_id=user_id
            )

            discovery = discovery_agent.get_discovery(discovery_id)

            # Send discovery complete message
            yield {
                "type": "status",
                "content": f"✅ Discovery completado: {discovery.domain}",
                "done": False,
            }

            yield {
                "type": "message",
                "role": MessageRole.ASSISTANT.value,
                "content": f"""## Discovery Completado

**Dominio**: {discovery.domain}
**Bounded Contexts**: {len(discovery.bounded_contexts)}
**Aggregates**: {len(discovery.aggregates)}
**Costo**: ${discovery.llm_cost_usd:.4f}

Ahora generando MasterPlan con 50 tareas...""",
                "done": False,
            }

            # Emit masterplan_generation_start event
            await self.websocket_manager.emit_to_session(
                session_id=session_id,
                event="masterplan_generation_start",
                data={"session_id": session_id}
            )

            # STEP 2: MasterPlan Generation (with WebSocket progress)
            # WebSocket events will be emitted automatically by MasterPlanGenerator
            masterplan_generator = MasterPlanGenerator(
                metrics_collector=self.metrics_collector,
                use_rag=True,  # Enable RAG to retrieve similar example masterplans
                websocket_manager=self.websocket_manager
            )

            masterplan_id = await masterplan_generator.generate_masterplan(
                discovery_id=discovery_id,
                session_id=session_id,  # Important: this is used for WebSocket events
                user_id=user_id
            )

            masterplan = masterplan_generator.get_masterplan(masterplan_id)

            # Format final result
            response = f"""## MasterPlan Generado ✅

**Proyecto**: {masterplan.project_name}
**Fases**: {masterplan.total_phases}
**Milestones**: {masterplan.total_milestones}
**Tareas**: {masterplan.total_tasks}

**Tech Stack**:
{chr(10).join([f"- **{k}**: {v}" for k, v in masterplan.tech_stack.items()])}

**Costo de Generación**: ${masterplan.generation_cost_usd:.4f}
**Costo Estimado Total**: ${masterplan.estimated_cost_usd:.2f}
**Duración Estimada**: {masterplan.estimated_duration_minutes} minutos

**MasterPlan ID**: `{masterplan_id}`

El plan completo ha sido guardado en la base de datos. Puedes comenzar la ejecución cuando estés listo."""

            # Save assistant message to conversation
            assistant_message = Message(
                content=response,
                role=MessageRole.ASSISTANT,
            )
            conversation.add_message(assistant_message)

            # Save to database
            self._save_message_to_db(
                conversation_id=conversation.conversation_id,
                role=MessageRole.ASSISTANT.value,
                content=response
            )

            yield {
                "type": "message",
                "role": MessageRole.ASSISTANT.value,
                "content": response,
                "metadata": {
                    "masterplan_id": str(masterplan_id),
                    "discovery_id": str(discovery_id),
                    "total_tasks": masterplan.total_tasks,
                    "estimated_cost_usd": masterplan.estimated_cost_usd,
                },
                "done": True,
            }

        except Exception as e:
            error_message = f"Error durante generación de MasterPlan: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            yield {
                "type": "error",
                "content": error_message,
                "done": True,
            }
