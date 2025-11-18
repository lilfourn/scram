from textual.app import App, ComposeResult
from textual.containers import Container, Grid
from textual.widgets import (
    Header,
    Footer,
    Input,
    Button,
    Label,
    Static,
    Log,
    ProgressBar,
)
from textual.screen import Screen
from textual.reactive import reactive
from textual.message import Message
from textual.worker import Worker

import asyncio

# Use absolute imports relative to project root
from src.core.events import event_bus, Event
from src.agent.state import AgentState
from src.agent.graph import app as agent_graph
from src.agent.nodes import fetching_engine


class WorkerStatus(Static):
    """Widget to display a single worker's status."""

    status = reactive("Idle")
    progress = reactive(0)

    def __init__(self, worker_id: int, **kwargs):
        super().__init__(**kwargs)
        self.worker_id = worker_id

    def compose(self) -> ComposeResult:
        yield Label(f"Worker {self.worker_id:02d}", classes="worker-id")
        yield Label(self.status, classes="worker-action")
        yield ProgressBar(total=100, show_eta=False, classes="worker-progress")

    def watch_status(self, status: str) -> None:
        if not self.is_mounted:
            return
        self.query_one(".worker-action", Label).update(status)

    def watch_progress(self, progress: int) -> None:
        if not self.is_mounted:
            return
        self.query_one(ProgressBar).progress = progress


class SetupScreen(Screen):
    """Screen for initial configuration."""

    # State for the wizard
    step = reactive(0)
    title_value = reactive("")
    objective_value = reactive("")
    url_value = reactive("")
    current_model = reactive("Google Gemini 3 Pro Preview")

    LOGO = """
███████╗ ██████╗██████╗  █████╗ ███╗   ███╗
██╔════╝██╔════╝██╔══██╗██╔══██╗████╗ ████║
███████╗██║     ██████╔╝███████║██╔████╔██║
╚════██║██║     ██╔══██╗██╔══██║██║╚██╔╝██║
███████║╚██████╗██║  ██║██║  ██║██║ ╚═╝ ██║
╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
    """

    COMMANDS = """
    /help show help
    /sessions list sessions
    /new start a new session
    /model switch model
    /theme switch theme
    /exit exit the app
    """

    def compose(self) -> ComposeResult:
        with Container(id="setup-container"):
            yield Label(self.LOGO, classes="logo")
            yield Label("v0.1.0", classes="version")

            yield Label(self.COMMANDS, classes="commands")

            # Dynamic content area (History)
            yield Container(id="history-area")

            # Input bar inside the container
            with Container(id="input-area"):
                yield Label(">", classes="prompt-symbol")
                yield Input(placeholder="Enter Objective...", id="setup-input")

            yield Label(self.current_model, classes="model-display", id="model-label")

    def on_mount(self) -> None:
        from src.core.config import config

        # Update model name from config if available, or keep default
        if config.DEFAULT_MODEL:
            # Format it nicely e.g. "gemini-3-pro-preview" -> "Google Gemini 3 Pro Preview"
            formatted = f"Google {config.DEFAULT_MODEL.replace('-', ' ').title()}"
            self.current_model = formatted
        self.query_one("#setup-input").focus()

    def watch_current_model(self, value: str) -> None:
        try:
            self.query_one("#model-label", Label).update(value)
        except:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            return

        # Handle exit command
        if value.lower() == "/exit":
            self.app.exit()
            return

        input_widget = self.query_one("#setup-input", Input)
        history_area = self.query_one("#history-area", Container)

        if self.step == 0:
            self.objective_value = value
            history_area.mount(
                Label(f"Objective: [bold green]{value}[/]", classes="history-item")
            )
            input_widget.placeholder = "Enter Seed URL..."
            input_widget.value = ""
            self.step = 1

        elif self.step == 1:
            self.url_value = value
            history_area.mount(
                Label(f"URL: [bold green]{value}[/]", classes="history-item")
            )
            input_widget.value = ""
            input_widget.placeholder = "Starting..."
            input_widget.disabled = True

            # Transition to dashboard
            self.app.push_screen("dashboard")
            if isinstance(self.app, ScramApp):
                # Pass a placeholder title, it will be updated by the agent
                self.app.start_agent(
                    "Generating Title...", self.objective_value, self.url_value
                )
            input_widget.placeholder = "Enter Seed URL..."
            input_widget.value = ""
            self.step = 1

        elif self.step == 1:
            self.url_value = value
            history_area.mount(
                Label(f"URL: [bold green]{value}[/]", classes="history-item")
            )
            input_widget.value = ""
            input_widget.placeholder = "Starting..."
            input_widget.disabled = True

            # Transition to dashboard
            self.app.push_screen("dashboard")
            if isinstance(self.app, ScramApp):
                # Pass a placeholder title, it will be updated by the agent
                self.app.start_agent(
                    "Generating Title...", self.objective_value, self.url_value
                )


class DashboardScreen(Screen):
    """Main dashboard screen."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Agent Status: Initializing...", id="agent-activity")

        with Grid(id="dashboard-grid"):
            # Worker Panel
            with Container(classes="panel", id="worker-panel"):
                yield Label("Worker Pool", classes="panel-title")
                # Create 10 worker widgets
                for i in range(10):
                    yield WorkerStatus(worker_id=i, id=f"worker-{i}")

            # Stats Panel
            with Container(classes="panel", id="stats-panel"):
                yield Label("Statistics", classes="panel-title")
                yield Static(
                    "Pages Scanned: 0", classes="stat-item", id="stat-pages_scanned"
                )
                yield Static(
                    "Items Extracted: 0", classes="stat-item", id="stat-items_extracted"
                )
                yield Static("Errors: 0", classes="stat-item", id="stat-errors")
                yield Static("Queue Size: 0", classes="stat-item", id="stat-queue_size")

            # Log Panel
            with Container(classes="panel", id="log-panel"):
                yield Label("System Logs", classes="panel-title")
                yield Log(id="log-output")

        yield Footer()


from src.agent.nodes import fetching_engine


class ScramApp(App):
    """The main TUI application."""

    CSS_PATH = "styles.tcss"
    SCREENS = {"setup": SetupScreen, "dashboard": DashboardScreen}

    def on_mount(self) -> None:
        self.push_screen("setup")
        # Subscribe to events
        event_bus.subscribe(self.handle_event)

    async def on_unmount(self) -> None:
        """Clean up resources on exit."""
        if fetching_engine.active:
            await fetching_engine.stop()
        # Ensure all tasks are cancelled if possible, though Textual handles worker cancellation.

    def start_agent(self, title: str, objective: str, url: str):
        """Start the agent in a background worker."""
        initial_state = AgentState(
            session_title=title,
            objective=objective,
            data_schema={},
            url_queue=[url],
            visited_urls=set(),
            extracted_data=[],
            current_url=None,
            current_content=None,
            is_relevant=False,
            next_urls=[],
        )

        self.run_worker(self._run_agent_loop(initial_state), exclusive=True)

    async def _run_agent_loop(self, state: AgentState):
        """Run the agent graph loop."""
        try:
            # We invoke the graph. Since it's a state machine, we might want to run it step-by-step
            # or just let it run. For now, let's just invoke it.
            # Note: The graph as defined currently runs until completion (queue empty).
            await agent_graph.ainvoke(state)
        except Exception as e:
            self.call_later(self.log_error, str(e))

    def log_error(self, message: str):
        if self.screen.id == "dashboard":
            self.screen.query_one("#log-output", Log).write_line(
                f"[red]ERROR: {message}[/]"
            )

    def handle_event(self, event: Event):
        """Handle events from the event bus."""
        # Schedule UI updates on the main thread
        self.call_later(self._update_ui, event)

    def _update_ui(self, event: Event):
        """Update UI elements based on event type."""
        if not self.screen or self.screen.id != "dashboard":
            return

        try:
            if event.type == "worker_status":
                worker_id = event.payload["worker_id"]
                status = event.payload["status"]
                progress = event.payload["progress"]
                worker_widget = self.screen.query_one(
                    f"#worker-{worker_id}", WorkerStatus
                )
                worker_widget.status = status
                worker_widget.progress = progress

            elif event.type == "agent_activity":
                status = event.payload["status"]
                self.screen.query_one("#agent-activity", Static).update(
                    f"Agent Status: {status}"
                )

            elif event.type == "stats_update":
                metric = event.payload["metric"]
                if "value" in event.payload:
                    value = event.payload["value"]
                    # Update specific stat widget
                    # Mapping metric names to IDs
                    # queue_size -> stat-queue_size
                    try:
                        widget = self.screen.query_one(f"#stat-{metric}", Static)
                        # Accessing renderable directly is not recommended, but for Static it holds the text
                        # Better to store state, but for now:
                        label = str(widget.renderable).split(":")[0]
                        widget.update(f"{label}: {value}")
                    except:
                        pass
                elif "increment" in event.payload:
                    try:
                        widget = self.screen.query_one(f"#stat-{metric}", Static)
                        text = str(widget.renderable)
                        label, val_str = text.split(":")
                        new_val = int(val_str.strip()) + event.payload["increment"]
                        widget.update(f"{label}: {new_val}")
                    except:
                        pass

            elif event.type == "log":
                message = event.payload["message"]
                self.screen.query_one("#log-output", Log).write_line(message)

        except Exception:
            # Ignore UI update errors (e.g. widget not found during transition)
            pass


if __name__ == "__main__":
    app = ScramApp()
    app.run()
