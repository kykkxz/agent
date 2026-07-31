from typing import Any

from flask import jsonify


class BizException(Exception):
    def __init__(self, code: int, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def success(data: Any = None, message: str = "success"):
    return jsonify({"code": 0, "message": message, "data": data})


def error_response(code: int, message: str, status_code: int):
    return jsonify({"code": code, "message": message, "data": None}), status_code
