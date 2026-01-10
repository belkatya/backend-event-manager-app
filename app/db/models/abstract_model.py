# app/db/models/abstract_model.py
from tortoise import fields, models
from tortoise.contrib.pydantic.creator import pydantic_model_creator


class TimestampMixin:
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class BaseModel(models.Model, TimestampMixin):
    id = fields.IntField(pk=True)

    class Meta:
        abstract = True