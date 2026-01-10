#app/db/models/category.py
# app/db/models/category.py
from tortoise import fields, models
from db.models.abstract_model import BaseModel


class Category(BaseModel):
    name = fields.CharField(max_length=100, unique=True)

    class Meta:
        table = "categories"

    def __str__(self):
        return self.name