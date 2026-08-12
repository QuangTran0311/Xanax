"""tools package – auto-registers all tool modules on import."""
from tools import xanax_tools  # noqa: F401 – side-effect: registers tools
from tools import builtin  # noqa: F401 – side-effect: registers built-in tools
