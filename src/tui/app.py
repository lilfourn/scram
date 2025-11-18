from textual.app import App, ComposeResult
from textual.containers import Container, Grid
from textual.widgets import (
    Header,
    Footer,
    Input,
    Label,
    Static,
    Log,
    ProgressBar,
    OptionList,
    DataTable,
    Button,
)
from textual.screen import Screen, ModalScreen
from textual.reactive import reactive
from textual.binding import Binding


# Use absolute imports relative to project root
from src.core.events import event_bus, Event
from src.agent.state import AgentState
from src.agent.graph import app as agent_graph
from src.agent.nodes import fetching_engine, gemini_client


class ReviewModal(ModalScreen):
    """Modal to review a data item with its screenshot."""

    def __init__(self, item: dict, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    def compose(self) -> ComposeResult:
        with Container(classes="modal-container"):
            yield Label("Data Verification", classes="modal-title")

            # Data Table
            yield DataTable(id="review-table")

            # Screenshot info (placeholder for actual image display if terminal supports it,
            # or path display)
            screenshot_path = self.item.get("_metadata", {}).get(
                "screenshot_path", "N/A"
            )
            yield Label(f"Screenshot: {screenshot_path}", classes="screenshot-path")

            with Container(classes="modal-buttons"):
                yield Button("Close", variant="primary", id="close-btn")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Field", "Value")

        for k, v in self.item.items():
            if k != "_metadata":
                table.add_row(str(k), str(v))

        # Add metadata rows
        if "_metadata" in self.item:
            for k, v in self.item["_metadata"].items():
                table.add_row(f"[dim]{k}[/]", f"[dim]{v}[/]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.dismiss()


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

    HELP_TEXT = """
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

            yield Label(self.HELP_TEXT, classes="commands")

            # Dynamic content area (History)
            yield Container(id="history-area")

            # Suggestions Area (Hidden by default)
            with Container(id="suggestions-area"):
                yield Label("Suggested Objectives:", classes="suggestion-label")
                yield OptionList(id="objective-options")

            # Input bar inside the container
            with Container(id="input-area"):
                yield Label(">", classes="prompt-symbol")
                yield Input(placeholder="Enter Seed URL...", id="setup-input")

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
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            return

        # Handle exit command
        if value.lower() == "/exit":
            self.app.exit()
            return

        # Handle theme command
        if value.lower() == "/theme":
            if isinstance(self.app, ScramApp):
                self.app.toggle_theme()
                self.query_one("#setup-input", Input).value = ""
                self.notify("Theme switched!")
            return

        input_widget = self.query_one("#setup-input", Input)
        history_area = self.query_one("#history-area", Container)

        if self.step == 0:
            # User entered URL
            self.url_value = value
            history_area.mount(
                Label(f"URL: [bold green]{value}[/]", classes="history-item")
            )

            # Show analyzing state
            input_widget.disabled = True
            input_widget.placeholder = "Analyzing URL..."
            input_widget.value = ""

            # Start analysis worker
            self.run_worker(self.analyze_url(value))

        elif self.step == 2:
            # User entered custom objective
            self.objective_value = value
            history_area.mount(
                Label(f"Objective: [bold green]{value}[/]", classes="history-item")
            )
            self.start_session()

    async def analyze_url(self, url: str):
        """Fetch and analyze the URL to generate suggestions."""
        try:
            # Fetch content (simple fetch)
            content, status, _ = await fetching_engine.fetch(url)

            if status != 200:
                self.notify(f"Failed to fetch URL: {status}", severity="error")
                # Fallback to manual entry
                self.step = 2
                self.query_one("#setup-input", Input).disabled = False
                self.query_one("#setup-input", Input).placeholder = "Enter Objective..."
                self.query_one("#setup-input", Input).focus()
                return

            # Analyze with AI
            analysis = await gemini_client.analyze_seed_url(url, content)

            # Update UI with suggestions
            summary = analysis.get("summary", "No summary available.")
            suggestions = analysis.get("suggestions", [])

            self.query_one("#history-area", Container).mount(
                Label(f"Summary: [italic]{summary}[/]", classes="history-item")
            )

            options = self.query_one("#objective-options", OptionList)
            options.clear_options()
            for suggestion in suggestions:
                options.add_option(suggestion)
            options.add_option("Custom Objective...")

            # Show suggestions
            self.query_one("#suggestions-area").add_class("visible")
            options.focus()

            self.step = 1  # Selection step

        except Exception as e:
            self.notify(f"Analysis failed: {e}", severity="error")
            # Fallback
            self.step = 2
            self.query_one("#setup-input", Input).disabled = False
            self.query_one("#setup-input", Input).placeholder = "Enter Objective..."
            self.query_one("#setup-input", Input).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle selection from the suggestions list."""
        selected_index = event.option_index
        options = self.query_one("#objective-options", OptionList)
        selected_text = str(options.get_option_at_index(selected_index).prompt)

        if selected_text == "Custom Objective...":
            # Switch to custom input
            self.query_one("#suggestions-area").remove_class("visible")
            input_widget = self.query_one("#setup-input", Input)
            input_widget.disabled = False
            input_widget.placeholder = "Enter Custom Objective..."
            input_widget.focus()
            self.step = 2
        else:
            self.objective_value = selected_text
            self.query_one("#history-area", Container).mount(
                Label(
                    f"Objective: [bold green]{selected_text}[/]", classes="history-item"
                )
            )
            self.start_session()

    def start_session(self):
        """Transition to dashboard and start the agent."""
        self.app.push_screen("dashboard")
        if isinstance(self.app, ScramApp):
            self.app.start_agent(
                "Generating Title...", self.objective_value, self.url_value
            )


class DashboardScreen(Screen):
    """Main dashboard screen."""

    latest_item = reactive(None)

    BINDINGS = [
        Binding("r", "show_review", "Review Data"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Agent Status: Initializing...", id="agent-activity")

        with Grid(id="dashboard-grid"):
            # Worker Panel
            with Container(classes="panel", id="worker-panel"):
                yield Label("Worker Pool", classes="panel-title")
                # Create worker widgets based on config
                from src.core.config import config

                for i in range(config.MAX_CONCURRENCY):
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

                yield Button("Review Latest Data", id="review-btn", variant="success")

            # Log Panel
            with Container(classes="panel", id="log-panel"):
                yield Label("System Logs", classes="panel-title")
                yield Log(id="log-output")

        yield Footer()

    def action_show_review(self):
        """Show review modal for the last extracted item."""
        # In a real app, we'd query the state or database.
        # For now, we can't easily access the running agent's state directly from here
        # without a shared store or event.
        # But we can listen to "data_extracted" events.
        self.app.notify("Review feature requires data stream.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "review-btn":
            # Trigger review of latest item if available
            # We need to store latest item in the app or screen
            if hasattr(self, "latest_item") and self.latest_item:
                self.app.push_screen(ReviewModal(self.latest_item))
            else:
                self.app.notify("No data extracted yet.")


class ScramApp(App):
    """The main TUI application."""

    CSS_PATH = "styles.tcss"
    SCREENS = {"setup": SetupScreen, "dashboard": DashboardScreen}

    # Available themes (class names in CSS)
    THEMES = ["theme-default", "theme-matrix", "theme-cyberpunk"]
    current_theme_index = 0

    def on_mount(self) -> None:
        self.push_screen("setup")
        # Subscribe to events
        event_bus.subscribe(self.handle_event)

    def toggle_theme(self) -> None:
        """Cycle through available themes."""
        # Remove current theme class
        current_theme = self.THEMES[self.current_theme_index]
        if current_theme != "theme-default":
            self.remove_class(current_theme)

        # Move to next
        self.current_theme_index = (self.current_theme_index + 1) % len(self.THEMES)
        next_theme = self.THEMES[self.current_theme_index]

        # Apply new theme class
        if next_theme != "theme-default":
            self.add_class(next_theme)

        self.notify(f"Switched to {next_theme.replace('theme-', '').title()} theme")

    async def on_unmount(self) -> None:
        """Clean up resources on exit."""
        # Ensure all tasks are cancelled if possible, though Textual handles worker cancellation.
        pass

    def start_agent(self, title: str, objective: str, url: str):
        """Start the agent in a background worker."""
        initial_state = AgentState(
            session_title=title,
            objective=objective,
            data_schema={},
            url_queue=[url],
            visited_urls=set(),
            failed_urls=set(),
            extracted_data=[],
            current_urls=[],
            current_contents=[],
            current_screenshots=[],
            relevant_flags=[],
            batch_next_urls=[],
            template_groups={},
            optimized_templates=set(),
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
                # Map metric IDs to their display labels
                metric_labels = {
                    "pages_scanned": "Pages Scanned",
                    "items_extracted": "Items Extracted",
                    "errors": "Errors",
                    "queue_size": "Queue Size",
                }

                if "value" in event.payload:
                    value = event.payload["value"]
                    try:
                        widget = self.screen.query_one(f"#stat-{metric}", Static)
                        label = metric_labels.get(
                            metric, metric.replace("_", " ").title()
                        )
                        widget.update(f"{label}: {value}")
                    except Exception:
                        pass
                elif "increment" in event.payload:
                    # Increment logic is temporarily disabled due to state management complexity
                    # in stateless widgets.
                    pass

            elif event.type == "data_extracted":
                # Store latest item for review
                if self.screen.id == "dashboard":
                    # Cast to DashboardScreen to access custom attribute
                    dashboard = self.screen
                    if isinstance(dashboard, DashboardScreen):
                        dashboard.latest_item = event.payload["item"]
                        dashboard.query_one(
                            "#review-btn", Button
                        ).label = "Review Latest Data (New)"

            elif event.type == "log":
                message = event.payload["message"]
                self.screen.query_one("#log-output", Log).write_line(message)

        except Exception as e:
            # Log error to file so we can see it
            import logging

            logging.getLogger(__name__).error(f"UI Update failed: {e}")


if __name__ == "__main__":
    app = ScramApp()
    app.run()
