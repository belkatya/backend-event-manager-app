# app/db/models/user.py
from tortoise import fields, models
from db.models.abstract_model import BaseModel


class User(BaseModel):
    email = fields.CharField(max_length=255, unique=True, index=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    hashed_password = fields.CharField(max_length=255)

    class Meta:
        table = "users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"