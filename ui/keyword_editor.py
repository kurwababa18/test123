"""
Keyword bucket editor - allows user to customize search terms for each market.
"""

from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Button, Label, TextArea
from textual import on
from typing import List, Callable

class KeywordEditorScreen(ModalScreen[List[str]]):
    """Modal screen for editing keyword buckets."""

    CSS = """
    KeywordEditorScreen {
        align: center middle;
    }

    #editor_dialog {
        width: 80;
        height: 30;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    #instructions {
        width: 100%;
        color: $text-muted;
        margin: 1 0;
    }

    #keyword_input {
        width: 100%;
        height: 15;
        border: solid $primary;
        margin: 1 0;
    }

    #button_container {
        width: 100%;
        height: 3;
        align: center middle;
        margin: 1 0;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, market_title: str, current_keywords: List[str], on_save: Callable):
        super().__init__()
        self.market_title = market_title
        self.current_keywords = current_keywords
        self.on_save_callback = on_save

    def compose(self):
        with Container(id="editor_dialog"):
            yield Label(f"Edit Keywords: {self.market_title[:50]}", id="title")
            yield Label("Enter keywords/phrases (one per line):", id="instructions")

            # Text area with current keywords
            keywords_text = "\n".join(self.current_keywords)
            yield TextArea(keywords_text, id="keyword_input")

            yield Label("💡 Tip: Use 'AND', 'OR', quotes for advanced searches", id="instructions")

            with Horizontal(id="button_container"):
                yield Button("Save", variant="primary", id="save_btn")
                yield Button("Cancel", variant="default", id="cancel_btn")

    @on(Button.Pressed, "#save_btn")
    def save_keywords(self):
        """Save the edited keywords."""
        textarea = self.query_one("#keyword_input", TextArea)
        text = textarea.text

        # Parse keywords (one per line, skip empty)
        keywords = [line.strip() for line in text.split('\n') if line.strip()]

        # Call the save callback
        if self.on_save_callback:
            self.on_save_callback(keywords)

        # Close the modal
        self.dismiss(keywords)

    @on(Button.Pressed, "#cancel_btn")
    def cancel_edit(self):
        """Cancel editing."""
        self.dismiss(self.current_keywords)
