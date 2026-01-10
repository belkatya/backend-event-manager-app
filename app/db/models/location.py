# app/db/models/location.py
from tortoise import fields, models
from db.models.abstract_model import BaseModel


class Location(BaseModel):
    city = fields.CharField(max_length=100, index=True)
    street = fields.CharField(max_length=255)
    house = fields.CharField(max_length=50)

    class Meta:
        table = "locations"

    def __str__(self):
        return f"{self.city}, {self.street}, {self.house}"