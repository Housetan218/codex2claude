EXIT_OK = 0
EXIT_CLAUDE_ERROR = 1
EXIT_TIMEOUT = 2
EXIT_LOCK_CONFLICT = 3
EXIT_INVALID_ARGS = 4
EXIT_STATE_ERROR = 5


class BridgeError(Exception):
    exit_code = EXIT_CLAUDE_ERROR


class LockConflictError(BridgeError):
    exit_code = EXIT_LOCK_CONFLICT


class StateCorruptionError(BridgeError):
    exit_code = EXIT_STATE_ERROR


class InvalidArgumentsError(BridgeError):
    exit_code = EXIT_INVALID_ARGS


class ClaudeTimeoutError(BridgeError):
    exit_code = EXIT_TIMEOUT


class ClaudeInvocationError(BridgeError):
    exit_code = EXIT_CLAUDE_ERROR
