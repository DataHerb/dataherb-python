IGNORED_FOLDERS_AND_FILES = [".git", ".dataherb", ".vscode"]

MESSAGE_CODE = {
    "MISSING": lambda x: f"{x} is missing",
    "FILE_NOT_FOUND": lambda x: f"{x} was not found",
    "FILE_FOUND": lambda x: f"{x} was found",
    "EXISTS": lambda x: f"{x} exists",
    "FREE_MESSAGE": lambda x: f"{x}",
}

STATUS_CODE = {
    "UNKNOWN": "unknown",
    "SUCCESS": "success",
    "WARNING": "warning",
    "ERROR": "error",
}
