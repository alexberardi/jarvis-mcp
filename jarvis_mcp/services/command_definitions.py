"""
Built-in command definitions and test cases for E2E command testing.

Ported from jarvis-node-setup IJarvisCommand implementations.
These definitions mirror what get_command_schema() and to_openai_tool_schema() return
for each command, enabling MCP-based E2E testing without a node environment.

DEFAULT_AVAILABLE_COMMANDS is the single source of truth. DEFAULT_CLIENT_TOOLS
is generated from it via _to_openai_tool_schema().
"""

from typing import Any


# =============================================================================
# Type mapping: CommandDefinition param type → OpenAI JSON Schema type
# =============================================================================

_TYPE_MAP: dict[str, str | dict[str, Any]] = {
    "string": "string",
    "float": "number",
    "int": "integer",
    "number": "number",
    "integer": "integer",
    "boolean": "boolean",
}


def _map_param_type(param_type: str) -> str | dict[str, Any]:
    """Map a CommandDefinition param type to OpenAI JSON Schema type."""
    if param_type.startswith("array<") and param_type.endswith(">"):
        inner = param_type[6:-1]
        return {"type": "array", "items": {"type": _TYPE_MAP.get(inner, inner)}}
    return _TYPE_MAP.get(param_type, param_type)


def _to_openai_tool_schema(cmd: dict[str, Any]) -> dict[str, Any]:
    """Convert a CommandDefinition dict to OpenAI tool schema format."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param in cmd.get("parameters", []):
        mapped_type = _map_param_type(param["type"])
        if isinstance(mapped_type, dict):
            prop: dict[str, Any] = {**mapped_type}
        else:
            prop = {"type": mapped_type}
        if param.get("description"):
            prop["description"] = param["description"]
        properties[param["name"]] = prop
        if param.get("required"):
            required.append(param["name"])

    tool: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": cmd["command_name"],
            "description": cmd["description"],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }

    # Copy through optional metadata fields
    for key in ("allow_direct_answer", "keywords", "examples", "antipatterns"):
        if key in cmd:
            tool[key] = cmd[key]

    return tool

# =============================================================================
# DEFAULT_AVAILABLE_COMMANDS
# CommandDefinition-shaped dicts matching IJarvisCommand.get_command_schema()
# =============================================================================

DEFAULT_AVAILABLE_COMMANDS: list[dict[str, Any]] = [
    {
        "command_name": "get_weather",
        "description": (
            "Get the current weather or forecast for a location. "
            "If no city is provided, use the user's default location."
        ),
        "allow_direct_answer": False,
        "parameters": [
            {
                "name": "city",
                "type": "string",
                "required": False,
                "description": "City name for weather lookup. Optional if user has a default location.",
            },
            {
                "name": "resolved_datetimes",
                "type": "array<string>",
                "required": True,
                "description": (
                    "ISO 8601 datetime strings resolved from date keys. "
                    "Always required; use today's start of day if user doesn't specify."
                ),
            },
            {
                "name": "unit_system",
                "type": "string",
                "required": False,
                "description": "Unit system: 'imperial' (default) or 'metric'.",
            },
        ],
        "keywords": [
            "weather", "forecast", "temperature", "rain", "snow", "sunny",
            "cloudy", "wind", "humidity", "hot", "cold", "warm",
        ],
        "examples": [
            {
                "voice_command": "What's the weather like?",
                "expected_parameters": {"resolved_datetimes": ["today"]},
                "is_primary": True,
            },
            {
                "voice_command": "What's the weather in Miami?",
                "expected_parameters": {"city": "Miami", "resolved_datetimes": ["today"]},
                "is_primary": False,
            },
            {
                "voice_command": "What's the forecast for tomorrow?",
                "expected_parameters": {"resolved_datetimes": ["tomorrow"]},
                "is_primary": False,
            },
        ],
        "critical_rules": [
            "Always include resolved_datetimes; use today if user doesn't specify a date",
            "Use get_weather for ALL weather-related queries — never use search_web for weather",
            "If the user asks about weather, temperature, forecast, rain, etc., always use this command",
        ],
        "antipatterns": [
            {
                "command_name": "search_web",
                "description": "Never use web search for weather queries. Always use get_weather.",
            },
        ],
    },
    {
        "command_name": "get_calendar_events",
        "description": "Retrieve calendar events for a given date or date range.",
        "allow_direct_answer": False,
        "parameters": [
            {
                "name": "resolved_datetimes",
                "type": "array<string>",
                "required": True,
                "description": (
                    "ISO 8601 datetime strings for the date range. "
                    "Always required; use today if user doesn't specify."
                ),
            },
        ],
        "keywords": [
            "calendar", "schedule", "appointment", "meeting", "event",
            "what's on", "plans", "busy", "free",
        ],
        "examples": [
            {
                "voice_command": "What's on my calendar today?",
                "expected_parameters": {"resolved_datetimes": ["today"]},
                "is_primary": True,
            },
            {
                "voice_command": "Show me my schedule for tomorrow",
                "expected_parameters": {"resolved_datetimes": ["tomorrow"]},
                "is_primary": False,
            },
            {
                "voice_command": "What meetings do I have next week?",
                "expected_parameters": {"resolved_datetimes": ["next_week"]},
                "is_primary": False,
            },
        ],
        "critical_rules": [
            "Always include resolved_datetimes; use today if user doesn't specify",
            "Use this for ALL calendar-related queries",
        ],
    },
    {
        "command_name": "answer_question",
        "description": (
            "Answer questions about established, stable knowledge — "
            "facts, definitions, history, science, geography, and biographies. "
            "Use ONLY for established, non-changing knowledge."
        ),
        "allow_direct_answer": True,
        "parameters": [
            {
                "name": "query",
                "type": "string",
                "required": True,
                "description": "Question about established, stable knowledge.",
            },
        ],
        "keywords": [
            "knowledge", "query", "what is", "who was", "who is",
            "when did", "where is", "how does", "define", "explain",
        ],
        "examples": [
            {
                "voice_command": "What is the capital of France?",
                "expected_parameters": {"query": "What is the capital of France?"},
                "is_primary": True,
            },
            {
                "voice_command": "Who was Albert Einstein?",
                "expected_parameters": {"query": "Who was Albert Einstein?"},
                "is_primary": False,
            },
        ],
        "critical_rules": [
            "Use ONLY for established, non-changing knowledge (facts, history, science, geography)",
            "Do NOT use for current events, live data, or real-time information",
            "Do NOT use for time zone queries — use get_current_time instead",
        ],
        "antipatterns": [
            {
                "command_name": "search_web",
                "description": (
                    "Current events, live information, election results, "
                    "'who won' recent races or championships, real-time data, breaking news."
                ),
            },
        ],
    },
    {
        "command_name": "search_web",
        "description": (
            "Perform a live web search for current information, stock prices, news, "
            "election results, or any real-time data. Use for dynamic, changing information."
        ),
        "allow_direct_answer": False,
        "parameters": [
            {
                "name": "query",
                "type": "string",
                "required": True,
                "description": "Search query for current or recent information.",
            },
        ],
        "keywords": [
            "search", "look up", "find", "current", "latest", "recent",
            "live", "real time", "news", "now", "today's news", "breaking",
        ],
        "examples": [
            {
                "voice_command": "Who won the senate race in Pennsylvania?",
                "expected_parameters": {"query": "Who won the senate race in Pennsylvania?"},
                "is_primary": True,
            },
            {
                "voice_command": "When is the next SpaceX launch?",
                "expected_parameters": {"query": "When is the next SpaceX launch?"},
                "is_primary": False,
            },
        ],
        "critical_rules": [
            "Use for questions requiring CURRENT, LIVE, or UP-TO-DATE information",
            "Do NOT use for established facts, historical information, or general knowledge",
            "Always call this tool for web search queries; do NOT answer directly from memory",
            "For 'what time is it in [location]' queries, use get_current_time instead",
        ],
        "antipatterns": [
            {
                "command_name": "answer_question",
                "description": "Stable facts, definitions, biographies, geography, historical dates.",
            },
            {
                "command_name": "get_weather",
                "description": "Weather conditions, temperature, forecasts. Always use get_weather for weather.",
            },
            {
                "command_name": "get_sports_scores",
                "description": "Game scores, results, 'how did [team] do', final scores.",
            },
            {
                "command_name": "get_current_time",
                "description": "Current time in a location, time zone queries.",
            },
        ],
    },
    {
        "command_name": "tell_joke",
        "description": "Tell a clean, family-friendly joke with an optional topic.",
        "allow_direct_answer": True,
        "parameters": [
            {
                "name": "topic",
                "type": "string",
                "required": False,
                "description": "Optional topic; omit for a random joke.",
            },
        ],
        "keywords": ["joke", "funny", "humor", "laugh", "comedy", "make me laugh"],
        "examples": [
            {
                "voice_command": "Tell me a joke",
                "expected_parameters": {},
                "is_primary": True,
            },
            {
                "voice_command": "Tell me a joke about animals",
                "expected_parameters": {"topic": "animals"},
                "is_primary": False,
            },
        ],
    },
    {
        "command_name": "calculate",
        "description": "Perform two-number arithmetic operations: addition, subtraction, multiplication, or division.",
        "allow_direct_answer": True,
        "parameters": [
            {
                "name": "num1",
                "type": "float",
                "required": True,
                "description": "First number.",
            },
            {
                "name": "num2",
                "type": "float",
                "required": True,
                "description": "Second number.",
            },
            {
                "name": "operation",
                "type": "string",
                "required": True,
                "description": "Operation: must be exactly 'add', 'subtract', 'multiply', or 'divide' (no synonyms).",
            },
        ],
        "keywords": ["calculate", "math", "add", "subtract", "multiply", "divide", "plus", "minus"],
        "examples": [
            {
                "voice_command": "What's 5 plus 3?",
                "expected_parameters": {"num1": 5, "num2": 3, "operation": "add"},
                "is_primary": True,
            },
            {
                "voice_command": "Divide 20 by 5",
                "expected_parameters": {"num1": 20, "num2": 5, "operation": "divide"},
                "is_primary": False,
            },
        ],
        "critical_rules": [
            "Map common terms: 'sum'/'plus'/'+' -> 'add', 'minus'/'-' -> 'subtract', 'times'/'*' -> 'multiply', 'divided by'/'/' -> 'divide'",
            "The operation parameter must be exactly one of: 'add', 'subtract', 'multiply', 'divide'",
        ],
    },
    {
        "command_name": "get_sports_scores",
        "description": "Retrieve final scores and results for active or recently completed games. Use for past game results and outcomes.",
        "allow_direct_answer": False,
        "parameters": [
            {
                "name": "team_name",
                "type": "string",
                "required": True,
                "description": "Team name as spoken; include city/school if said (e.g., 'Lakers', 'Alabama').",
            },
            {
                "name": "resolved_datetimes",
                "type": "array<string>",
                "required": True,
                "description": "Date keys like 'today', 'yesterday', 'last_weekend'. Always required; use 'today' if user doesn't specify.",
            },
        ],
        "keywords": [
            "scores", "won", "lost", "win", "lose", "result",
            "game result", "how did", "final score", "outcome", "beat", "defeated",
        ],
        "examples": [
            {
                "voice_command": "How did the Giants do?",
                "expected_parameters": {"team_name": "Giants", "resolved_datetimes": ["today"]},
                "is_primary": True,
            },
            {
                "voice_command": "What's the score of the Lakers game today?",
                "expected_parameters": {"team_name": "Lakers", "resolved_datetimes": ["today"]},
                "is_primary": False,
            },
        ],
        "critical_rules": [
            "Always include resolved_datetimes; if no date is specified, use today",
            "Always call this tool for sports results; do NOT answer from memory",
            "Use for questions about PAST performance, results, scores, or 'how did [team] do'",
            "For championship winners or season outcomes, use search_web instead",
        ],
        "antipatterns": [
            {
                "command_name": "search_web",
                "description": "Championship winners, season outcomes, 'who won the Super Bowl/World Series'.",
            },
        ],
    },
    {
        "command_name": "set_timer",
        "description": (
            "Set a timer for a specified duration. The timer runs in the background "
            "and announces via voice when complete. Convert spoken time to total seconds "
            "(e.g., '5 minutes' = 300, '1 hour 30 minutes' = 5400)."
        ),
        "allow_direct_answer": False,
        "parameters": [
            {
                "name": "duration_seconds",
                "type": "int",
                "required": True,
                "description": (
                    "Total duration in seconds. Convert spoken time: "
                    "'30 seconds' -> 30, '5 minutes' -> 300, '1 hour' -> 3600."
                ),
            },
            {
                "name": "label",
                "type": "string",
                "required": False,
                "description": "Optional label for the timer (e.g., 'pasta', 'laundry').",
            },
        ],
        "keywords": ["timer", "set timer", "alarm", "remind", "reminder", "countdown", "wake me", "notify me"],
        "examples": [
            {
                "voice_command": "Set a timer for 5 minutes",
                "expected_parameters": {"duration_seconds": 300},
                "is_primary": True,
            },
            {
                "voice_command": "Set a 10 minute timer for pasta",
                "expected_parameters": {"duration_seconds": 600, "label": "pasta"},
                "is_primary": False,
            },
        ],
        "rules": [
            "Always convert spoken time to total seconds before calling",
            "Extract labels from context: 'timer for pasta' -> label='pasta'",
            "Compound times must be summed: '2 minutes 30 seconds' -> 150 seconds",
        ],
        "critical_rules": [
            "Time conversion: 1 minute = 60 seconds, 1 hour = 3600 seconds",
            "The duration_seconds parameter must be a positive integer",
        ],
    },
    {
        "command_name": "get_current_time",
        "description": "Get the current time in a specific city, state, or country. Use for time zone queries like 'what time is it in Tokyo?'",
        "allow_direct_answer": True,
        "parameters": [
            {
                "name": "location",
                "type": "string",
                "required": True,
                "description": "City, state, or country name (e.g., 'Tokyo', 'California', 'London').",
            },
        ],
        "keywords": ["time", "current time", "what time", "time zone", "timezone", "clock", "time in"],
        "examples": [
            {
                "voice_command": "What time is it in California?",
                "expected_parameters": {"location": "California"},
                "is_primary": True,
            },
            {
                "voice_command": "What time is it in Tokyo?",
                "expected_parameters": {"location": "Tokyo"},
                "is_primary": False,
            },
        ],
        "critical_rules": [
            "Use this command for questions about the current time in a location",
            "This is for TIME queries, not weather — 'what time is it' is NOT weather",
            "Extract just the location name without extra words",
        ],
        "antipatterns": [
            {
                "command_name": "get_weather",
                "description": "Weather conditions, temperature, forecasts. 'What time is it' is NOT weather.",
            },
            {
                "command_name": "search_web",
                "description": "General web searches. Use get_current_time for time queries.",
            },
        ],
    },
]


# =============================================================================
# DEFAULT_CLIENT_TOOLS
# Generated from DEFAULT_AVAILABLE_COMMANDS via _to_openai_tool_schema()
# =============================================================================

DEFAULT_CLIENT_TOOLS: list[dict[str, Any]] = [
    _to_openai_tool_schema(cmd) for cmd in DEFAULT_AVAILABLE_COMMANDS
]


# =============================================================================
# BUILTIN_TEST_CASES
# Ported from jarvis-node-setup/test_command_parsing.py
# Date-dependent expected_params omit resolved_datetimes (tested implicitly)
# =============================================================================

BUILTIN_TEST_CASES: list[dict[str, Any]] = [
    # ===== WEATHER (7 tests) =====
    {
        "category": "weather",
        "voice_command": "What's the weather like?",
        "expected_command": "get_weather",
        "expected_params": {},
        "description": "Basic current weather request (no city)",
    },
    {
        "category": "weather",
        "voice_command": "What's the weather in Miami?",
        "expected_command": "get_weather",
        "expected_params": {"city": "Miami"},
        "description": "Current weather with city specified",
    },
    {
        "category": "weather",
        "voice_command": "How's the weather in New York today?",
        "expected_command": "get_weather",
        "expected_params": {"city": "New York"},
        "description": "Current weather with city and today",
    },
    {
        "category": "weather",
        "voice_command": "What's the forecast for Los Angeles tomorrow?",
        "expected_command": "get_weather",
        "expected_params": {"city": "Los Angeles"},
        "description": "Forecast with city and tomorrow",
    },
    {
        "category": "weather",
        "voice_command": "Weather forecast for Chicago on the day after tomorrow",
        "expected_command": "get_weather",
        "expected_params": {"city": "Chicago"},
        "description": "Forecast with city and day after tomorrow",
    },
    {
        "category": "weather",
        "voice_command": "What's the weather like in metric units?",
        "expected_command": "get_weather",
        "expected_params": {"unit_system": "metric"},
        "description": "Current weather with unit system specified",
    },
    {
        "category": "weather",
        "voice_command": "What is the forecast for Seattle this weekend",
        "expected_command": "get_weather",
        "expected_params": {"city": "Seattle"},
        "description": "Forecast with city and date range",
    },
    # ===== CALENDAR (6 tests) =====
    {
        "category": "calendar",
        "voice_command": "What's on my calendar today?",
        "expected_command": "get_calendar_events",
        "expected_params": {},
        "description": "Calendar events for today",
    },
    {
        "category": "calendar",
        "voice_command": "Show me my schedule for tomorrow",
        "expected_command": "get_calendar_events",
        "expected_params": {},
        "description": "Calendar events for tomorrow",
    },
    {
        "category": "calendar",
        "voice_command": "What appointments do I have the day after tomorrow?",
        "expected_command": "get_calendar_events",
        "expected_params": {},
        "description": "Calendar events for day after tomorrow",
    },
    {
        "category": "calendar",
        "voice_command": "Show my calendar for this weekend",
        "expected_command": "get_calendar_events",
        "expected_params": {},
        "description": "Calendar events for weekend",
    },
    {
        "category": "calendar",
        "voice_command": "What meetings do I have next week?",
        "expected_command": "get_calendar_events",
        "expected_params": {},
        "description": "Calendar events for next week",
    },
    {
        "category": "calendar",
        "voice_command": "Read my calendar",
        "expected_command": "get_calendar_events",
        "expected_params": {},
        "description": "Basic calendar request",
    },
    # ===== KNOWLEDGE (6 tests) =====
    {
        "category": "knowledge",
        "voice_command": "What is the capital of France?",
        "expected_command": "answer_question",
        "expected_params": {"query": "What is the capital of France?"},
        "description": "Basic knowledge question",
    },
    {
        "category": "knowledge",
        "voice_command": "Who was Albert Einstein?",
        "expected_command": "answer_question",
        "expected_params": {"query": "Who was Albert Einstein?"},
        "description": "Person-related knowledge question",
    },
    {
        "category": "knowledge",
        "voice_command": "When did World War II end?",
        "expected_command": "answer_question",
        "expected_params": {"query": "When did World War II end?"},
        "description": "Historical knowledge question",
    },
    {
        "category": "knowledge",
        "voice_command": "How does photosynthesis work?",
        "expected_command": "answer_question",
        "expected_params": {"query": "How does photosynthesis work?"},
        "description": "Science knowledge question",
    },
    {
        "category": "knowledge",
        "voice_command": "Where is Mount Everest located?",
        "expected_command": "answer_question",
        "expected_params": {"query": "Where is Mount Everest located?"},
        "description": "Geography knowledge question",
    },
    {
        "category": "knowledge",
        "voice_command": "Explain quantum physics",
        "expected_command": "answer_question",
        "expected_params": {"query": "Explain quantum physics"},
        "description": "Complex topic explanation request",
    },
    # ===== SEARCH (8 tests) =====
    {
        "category": "search",
        "voice_command": "Who won the senate race in Pennsylvania?",
        "expected_command": "search_web",
        "expected_params": {"query": "Who won the senate race in Pennsylvania?"},
        "description": "Current election results search",
    },
    {
        "category": "search",
        "voice_command": "What time is it in California?",
        "expected_command": "get_current_time",
        "expected_params": {"location": "California"},
        "description": "Timezone query (should route to get_current_time)",
    },
    {
        "category": "search",
        "voice_command": "What's the latest news about Tesla stock?",
        "expected_command": "search_web",
        "expected_params": {"query": "What's the latest news about Tesla stock?"},
        "description": "Current market/news search",
    },
    {
        "category": "search",
        "voice_command": "When is the next SpaceX launch?",
        "expected_command": "search_web",
        "expected_params": {"query": "When is the next SpaceX launch?"},
        "description": "Upcoming event search",
    },
    {
        "category": "search",
        "voice_command": "What's the current weather in Miami?",
        "expected_command": "get_weather",
        "expected_params": {"city": "Miami"},
        "description": "Weather query should route to get_weather, not search_web",
    },
    {
        "category": "search",
        "voice_command": "Search for breaking news about artificial intelligence",
        "expected_command": "search_web",
        "expected_params": {},
        "description": "Explicit search request",
    },
    {
        "category": "search",
        "voice_command": "Find the latest information about COVID vaccines",
        "expected_command": "search_web",
        "expected_params": {},
        "description": "Current health information search",
    },
    # ===== JOKES (4 tests) =====
    {
        "category": "jokes",
        "voice_command": "Tell me a joke",
        "expected_command": "tell_joke",
        "expected_params": {},
        "description": "Basic joke request (no topic)",
    },
    {
        "category": "jokes",
        "voice_command": "Tell me a joke about programming",
        "expected_command": "tell_joke",
        "expected_params": {"topic": "programming"},
        "description": "Joke with specific topic",
    },
    {
        "category": "jokes",
        "voice_command": "Tell me a joke about animals",
        "expected_command": "tell_joke",
        "expected_params": {"topic": "animals"},
        "description": "Joke with different topic",
    },
    {
        "category": "jokes",
        "voice_command": "Make me laugh with a joke about technology",
        "expected_command": "tell_joke",
        "expected_params": {"topic": "technology"},
        "description": "Joke with topic using different phrasing",
    },
    # ===== CALCULATOR (8 tests) =====
    {
        "category": "calculator",
        "voice_command": "What's 5 plus 3?",
        "expected_command": "calculate",
        "expected_params": {"num1": 5, "num2": 3, "operation": "add"},
        "description": "Basic addition",
    },
    {
        "category": "calculator",
        "voice_command": "Calculate 10 minus 4",
        "expected_command": "calculate",
        "expected_params": {"num1": 10, "num2": 4, "operation": "subtract"},
        "description": "Subtraction with different phrasing",
    },
    {
        "category": "calculator",
        "voice_command": "What is 6 times 7?",
        "expected_command": "calculate",
        "expected_params": {"num1": 6, "num2": 7, "operation": "multiply"},
        "description": "Multiplication",
    },
    {
        "category": "calculator",
        "voice_command": "Divide 20 by 5",
        "expected_command": "calculate",
        "expected_params": {"num1": 20, "num2": 5, "operation": "divide"},
        "description": "Division",
    },
    {
        "category": "calculator",
        "voice_command": "Add 15 and 25 together",
        "expected_command": "calculate",
        "expected_params": {"num1": 15, "num2": 25, "operation": "add"},
        "description": "Addition with 'and' conjunction",
    },
    {
        "category": "calculator",
        "voice_command": "What's the sum of 8 and 12?",
        "expected_command": "calculate",
        "expected_params": {"num1": 8, "num2": 12, "operation": "add"},
        "description": "Addition using 'sum' terminology",
    },
    {
        "category": "calculator",
        "voice_command": "What's five plus 3?",
        "expected_command": "calculate",
        "expected_params": {"num1": 5, "num2": 3, "operation": "add"},
        "description": "Addition with written number",
    },
    {
        "category": "calculator",
        "voice_command": "Calculate ten minus four",
        "expected_command": "calculate",
        "expected_params": {"num1": 10, "num2": 4, "operation": "subtract"},
        "description": "Subtraction with written numbers",
    },
    # ===== SPORTS (18 tests) =====
    {
        "category": "sports",
        "voice_command": "How did the Giants do?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Giants"},
        "description": "Basic sports score request",
    },
    {
        "category": "sports",
        "voice_command": "What's the score of the Yankees game?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Yankees"},
        "description": "Score request with different team",
    },
    {
        "category": "sports",
        "voice_command": "How did the New York Giants do?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "New York Giants"},
        "description": "Score with location disambiguation",
    },
    {
        "category": "sports",
        "voice_command": "What's the score of the Carolina Panthers game?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Carolina Panthers"},
        "description": "Score with city/team combo",
    },
    {
        "category": "sports",
        "voice_command": "How did the Giants do yesterday?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Giants"},
        "description": "Score with relative date",
    },
    {
        "category": "sports",
        "voice_command": "What was the score of the Yankees game yesterday?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Yankees"},
        "description": "Score with relative date",
    },
    {
        "category": "sports",
        "voice_command": "How did the Baltimore Orioles do last weekend?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Baltimore Orioles"},
        "description": "Score with date range",
    },
    {
        "category": "sports",
        "voice_command": "What was the Chicago Bulls score last weekend?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Chicago Bulls"},
        "description": "Score with date range",
    },
    {
        "category": "sports",
        "voice_command": "How did the Cowboys do?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Cowboys"},
        "description": "Score with today implied",
    },
    {
        "category": "sports",
        "voice_command": "What's the score of the Warriors game tomorrow?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Warriors"},
        "description": "Score with relative date",
    },
    {
        "category": "sports",
        "voice_command": "What was the score of the Panthers game yesterday?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Panthers"},
        "description": "Score with relative date",
    },
    {
        "category": "sports",
        "voice_command": "How did the Eagles do last weekend?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Eagles"},
        "description": "Score with date range",
    },
    {
        "category": "sports",
        "voice_command": "What's the score of the Lakers game today?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Lakers"},
        "description": "Score with today",
    },
    {
        "category": "sports",
        "voice_command": "How did the Buccaneers do?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Buccaneers"},
        "description": "Score with today implied",
    },
    {
        "category": "sports",
        "voice_command": "Did the Steelers win?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Steelers"},
        "description": "Flexibility: 'Did X win' pattern",
    },
    {
        "category": "sports",
        "voice_command": "What was the Mets score?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Mets"},
        "description": "Flexibility: 'What was the X score' pattern",
    },
    {
        "category": "sports",
        "voice_command": "Final score for the Denver Broncos?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Denver Broncos"},
        "description": "Flexibility: 'Final score for X' pattern",
    },
    {
        "category": "sports",
        "voice_command": "How'd the Packers do last night?",
        "expected_command": "get_sports_scores",
        "expected_params": {"team_name": "Packers"},
        "description": "Flexibility: contraction with 'last night'",
    },
    # ===== TIMERS (14 tests) =====
    {
        "category": "timers",
        "voice_command": "Set a timer for 30 seconds",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 30},
        "description": "Timer for seconds only",
    },
    {
        "category": "timers",
        "voice_command": "Timer for 45 seconds",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 45},
        "description": "Timer without 'set' prefix",
    },
    {
        "category": "timers",
        "voice_command": "Set a timer for 5 minutes",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 300},
        "description": "Timer for 5 minutes",
    },
    {
        "category": "timers",
        "voice_command": "Timer for ten minutes",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 600},
        "description": "Timer with written-out number",
    },
    {
        "category": "timers",
        "voice_command": "Set a 15 minute timer",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 900},
        "description": "Timer with duration before 'timer'",
    },
    {
        "category": "timers",
        "voice_command": "Set a timer for 1 hour",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 3600},
        "description": "Timer for 1 hour",
    },
    {
        "category": "timers",
        "voice_command": "Timer for 2 hours",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 7200},
        "description": "Timer for 2 hours",
    },
    {
        "category": "timers",
        "voice_command": "Set a timer for 1 hour and 30 minutes",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 5400},
        "description": "Compound timer: 1h 30m",
    },
    {
        "category": "timers",
        "voice_command": "Timer for 2 minutes 30 seconds",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 150},
        "description": "Compound timer: 2m 30s",
    },
    {
        "category": "timers",
        "voice_command": "Set a 10 minute timer for pasta",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 600, "label": "pasta"},
        "description": "Timer with label",
    },
    {
        "category": "timers",
        "voice_command": "Timer for 20 minutes for the laundry",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 1200, "label": "laundry"},
        "description": "Timer with label (longer phrase)",
    },
    {
        "category": "timers",
        "voice_command": "Set a nap timer for 30 minutes",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 1800, "label": "nap"},
        "description": "Timer with label before duration",
    },
    {
        "category": "timers",
        "voice_command": "Remind me in 15 minutes",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 900},
        "description": "Casual: 'remind me' phrasing",
    },
    {
        "category": "timers",
        "voice_command": "Wake me up in 30 minutes",
        "expected_command": "set_timer",
        "expected_params": {"duration_seconds": 1800},
        "description": "Casual: 'wake me up' phrasing",
    },
]
