class NetioException(Exception):
    """Base exception for Device"""


class CommunicationError(NetioException):
    """Communication with Device failed"""


class AuthError(NetioException):
    """Authentication missing, or invalid"""


class UnknownOutputId(NetioException):
    """ Unknown output ID """
