from aiogram.fsm.state import StatesGroup, State

class ManualMonitorState(StatesGroup):
    selecting_category = State()
    selecting_model = State()
    selecting_publish_mode = State()
    selecting_targets = State()
    toggle_moderation = State()
    toggle_rewrite = State()
    confirm_launch = State()

    editing_trim_lines = State()
    editing_trim_phrases = State()
