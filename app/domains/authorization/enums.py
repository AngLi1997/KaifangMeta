from enum import StrEnum


class MethodType(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class MenuType(StrEnum):
    CATALOG = "catalog"
    MENU = "menu"
