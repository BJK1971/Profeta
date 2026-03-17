class DataNotFoundException(Exception):
    """Exception raised when data is not found.
    This exception is used to indicate that the requested data could not be found in the system.
    """

    def __init__(self, arg1, arg2=None):
        super(DataNotFoundException, self).__init__(arg1, arg2)
        self.arg1 = arg1
        self.arg2 = arg2
