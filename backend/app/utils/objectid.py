from bson import ObjectId
from typing import Annotated, Union

from pydantic import BeforeValidator, PlainSerializer


def to_objectid(value: Union[str, ObjectId]) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    raise ValueError(f"Invalid ObjectId: {value}")


def object_id_valid(value: Union[str, ObjectId]) -> bool:
    if isinstance(value, ObjectId):
        return True
    if isinstance(value, str):
        return ObjectId.is_valid(value)
    return False


def _objectid_validate(v: Union[str, ObjectId]) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("invalid ObjectId")


PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(_objectid_validate),
    PlainSerializer(lambda x: str(x), return_type=str),
]
