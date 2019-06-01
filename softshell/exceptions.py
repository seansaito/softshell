class VariableNotFoundError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message


class VariableNotDeclaredAtLineError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message


class LoadConfigError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message


class FileEditFailedError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message
