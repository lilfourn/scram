from __future__ import annotations
import logging
from typing import cast

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    Input,
    Label,
    Log,
    ProgressBar,
    OptionList,
    DataTable,
    Button,
    RichLog,
    LoadingIndicator,
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

            # Screenshot info
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


class DashboardScreen(Screen):
    """Main dashboard screen."""

    latest_item = reactive(None)
    stats = reactive(
        {
            "pages_scanned": 0,
            "items_extracted": 0,
            "queue_size": 0,
            "errors": 0,
            "bandwidth_saved": "0 MB",
        }
    )

    BINDINGS = [
        Binding("r", "show_review", "Review Data"),
    ]

    def __init__(self, session_title: str, objective: str, seed_url: str, **kwargs):
        super().__init__(**kwargs)
        self.session_title = session_title
        self.objective = objective
        self.seed_url = seed_url

    def compose(self) -> ComposeResult:
        yield Header()

        # Main Layout
        with Container(id="dashboard-container"):
            # Hero Status Section
            with Container(classes="status-card"):
                yield Label("Initializing...", id="main-status")
                yield ProgressBar(total=100, show_eta=False, id="activity-pulse")

            # Metrics Row
            with Horizontal(classes="metrics-row"):
                with Vertical(classes="metric-item"):
                    yield Label("Pages Scanned", classes="metric-label")
                    yield Label("0", id="stat-pages_scanned", classes="metric-value")

                with Vertical(classes="metric-item"):
                    yield Label("Items Extracted", classes="metric-label")
                    yield Label("0", id="stat-items_extracted", classes="metric-value")

                with Vertical(classes="metric-item"):
                    yield Label("Queue Size", classes="metric-label")
                    yield Label("0", id="stat-queue_size", classes="metric-value")

                with Vertical(classes="metric-item"):
                    yield Label("Errors", classes="metric-label")
                    yield Label("0", id="stat-errors", classes="metric-value")

                with Vertical(classes="metric-item"):
                    yield Label("Bandwidth Saved", classes="metric-label")
                    yield Label(
                        "0 MB", id="stat-bandwidth_saved", classes="metric-value"
                    )

            # Activity Feed (Replaces Worker Pool)
            with Container(classes="activity-container"):
                yield Label("Live Activity", classes="section-title")
                yield RichLog(
                    id="activity-feed", wrap=True, highlight=True, markup=True
                )

            # Review Button
            yield Button("Review Latest Data", id="review-btn", variant="success")

            # System Logs (Collapsible/Secondary)
            with Container(classes="logs-container"):
                yield Label("System Logs", classes="section-title")
                # Changed from Log to RichLog for better wrapping
                yield RichLog(id="log-output", wrap=True, highlight=True, markup=True)

        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted. Starts the agent."""
        self.query_one("#log-output", RichLog).write(
            "Dashboard ready. Starting agent..."
        )
        # Start the agent now that the UI is ready to receive events
        if hasattr(self.app, "start_agent"):
            cast(ScramApp, self.app).start_agent(
                self.session_title, self.objective, self.seed_url
            )

    def action_show_review(self):
        """Show review modal for the last extracted item."""
        if self.latest_item:
            self.app.push_screen(ReviewModal(self.latest_item))
        else:
            self.app.notify("No data extracted yet.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "review-btn":
            self.action_show_review()


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
    /model switch model
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
                yield LoadingIndicator(id="loading-indicator", classes="hidden")

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
            if hasattr(self.app, "toggle_theme"):
                cast(ScramApp, self.app).toggle_theme()
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
            input_widget.value = ""

            # Toggle visibility
            input_widget.add_class("hidden")
            self.query_one(".prompt-symbol").add_class("hidden")
            self.query_one("#loading-indicator").remove_class("hidden")

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

                # Restore UI
                self.query_one("#loading-indicator").add_class("hidden")
                self.query_one(".prompt-symbol").remove_class("hidden")
                input_widget = self.query_one("#setup-input", Input)
                input_widget.remove_class("hidden")
                input_widget.disabled = False
                input_widget.placeholder = "Enter Objective..."
                input_widget.focus()
                return

            # Analyze with AI
            analysis = await gemini_client.analyze_seed_url(url, content)

            # Update UI with suggestions
            summary = analysis.get("summary", "No summary available.")
            suggestions = analysis.get("suggestions", [])

            self.query_one("#history-area", Container).mount(
                Label(f"Summary: [italic]{summary}[/]", classes="history-item")
            )

            # Restore UI (hide loading)
            self.query_one("#loading-indicator").add_class("hidden")
            self.query_one(".prompt-symbol").remove_class("hidden")
            # Keep input hidden or disabled? We move to selection step.
            # Actually, we want to show options now.

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

            # Restore UI
            self.query_one("#loading-indicator").add_class("hidden")
            self.query_one(".prompt-symbol").remove_class("hidden")
            input_widget = self.query_one("#setup-input", Input)
            input_widget.remove_class("hidden")
            input_widget.disabled = False
            input_widget.placeholder = "Enter Objective..."
            input_widget.focus()

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
        # Instantiate DashboardScreen manually with parameters
        dashboard = DashboardScreen(
            session_title="Generating Title...",
            objective=self.objective_value,
            seed_url=self.url_value,
            id="dashboard",
        )
        self.app.push_screen(dashboard)


class ScramApp(App):
    """The main TUI application."""

    CSS_PATH = "styles.tcss"
    # Only setup is needed here, dashboard is pushed manually
    SCREENS = {"setup": SetupScreen}

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
            compressed_history="",
            recent_activity=[],
        )

        self.run_worker(self._run_agent_loop(initial_state), exclusive=True)

    async def _run_agent_loop(self, state: AgentState):
        """Run the agent graph loop."""
        try:
            await agent_graph.ainvoke(state)
        except Exception as e:
            self.call_later(self.log_error, str(e))

    def log_error(self, message: str):
        if self.screen.id == "dashboard":
            self.screen.query_one("#log-output", RichLog).write(
                f"[red]ERROR: {message}[/]"
            )

    def handle_event(self, event: Event):
        """Handle events from the event bus."""
        # Schedule UI updates on the main thread
        self.call_later(self._update_ui, event)

    def _update_ui(self, event: Event):
        """Update UI elements based on event type."""
        # Only update if we are on the dashboard
        if not self.screen or self.screen.id != "dashboard":
            return

        try:
            dashboard = cast(DashboardScreen, self.screen)

            if event.type == "worker_status":
                # Convert worker status to activity feed entry
                status = event.payload["status"]
                worker_id = event.payload["worker_id"]

                # Only log interesting statuses to avoid spam
                if status not in ["Idle", "Error"]:
                    activity_feed = dashboard.query_one("#activity-feed", RichLog)
                    activity_feed.write(f"[dim]Worker {worker_id:02d}:[/] {status}")

                if status == "Error":
                    activity_feed = dashboard.query_one("#activity-feed", RichLog)
                    activity_feed.write(
                        f"[red bold]Worker {worker_id:02d}: Error occurred[/]"
                    )

            elif event.type == "agent_activity":
                status = event.payload["status"]
                dashboard.query_one("#main-status", Label).update(status)

                # Pulse the progress bar
                bar = dashboard.query_one("#activity-pulse", ProgressBar)
                if bar.percentage is not None and bar.percentage < 100:
                    bar.advance(5)
                else:
                    bar.progress = 0

            elif event.type == "stats_update":
                metric = event.payload["metric"]
                if "value" in event.payload:
                    dashboard.stats[metric] = event.payload["value"]
                elif "increment" in event.payload:
                    # Ensure it's an int before adding
                    current = dashboard.stats.get(metric, 0)
                    if isinstance(current, int):
                        dashboard.stats[metric] = current + event.payload["increment"]

                # Update Label
                try:
                    dashboard.query_one(f"#stat-{metric}", Label).update(
                        str(dashboard.stats[metric])
                    )
                except Exception:
                    pass

            elif event.type == "data_extracted":
                # Store latest item for review
                if isinstance(dashboard, DashboardScreen):
                    dashboard.latest_item = event.payload["item"]
                    dashboard.query_one(
                        "#review-btn", Button
                    ).label = "Review Latest Data (New)"

                    # Log to activity feed
                    activity_feed = dashboard.query_one("#activity-feed", RichLog)
                    activity_feed.write(f"[green]✅ Data Extracted[/]")

            elif event.type == "log":
                message = event.payload["message"]
                # Use RichLog.write instead of Log.write_line
                dashboard.query_one("#log-output", RichLog).write(message)

        except Exception as e:
            # Log error to file so we can see it
            logging.getLogger(__name__).error(f"UI Update failed: {e}")


if __name__ == "__main__":
    app = ScramApp()
    app.run()
