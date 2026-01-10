# app/db/models/event.py
from tortoise import fields, models
from db.models.abstract_model import BaseModel
from db.models.location import Location
from db.models.user import User
from db.models.category import Category


class Event(BaseModel):
    title = fields.CharField(max_length=255, index=True)
    short_description = fields.TextField()
    full_description = fields.TextField()
    date = fields.DateField(index=True)
    time = fields.TimeField()

    # Foreign keys
    location: fields.ForeignKeyRelation[Location] = fields.ForeignKeyField(
        "server.Location",
        related_name="events"
    )
    organizer: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "server.User",
        related_name="organized_events"
    )

    # Count fields
    likes_count = fields.IntField(default=0)
    participants_count = fields.IntField(default=0)

    # Many-to-many relationships
    categories: fields.ManyToManyRelation[Category] = fields.ManyToManyField(
        "server.Category",
        related_name="events",
        through="event_categories"
    )

    # Users who liked this event
    liked_by: fields.ManyToManyRelation[User] = fields.ManyToManyField(
        "server.User",
        related_name="liked_events",
        through="user_event_likes",
        forward_key="user_id",
        backward_key="event_id"
    )

    # Users registered for this event
    participants: fields.ManyToManyRelation[User] = fields.ManyToManyField(
        "server.User",
        related_name="registered_events",
        through="user_event_registrations",
        forward_key="user_id",
        backward_key="event_id"
    )

    class Meta:
        table = "events"
        indexes = [
            ("date", "time"),
            ("likes_count",),
            ("participants_count",),
        ]

    def __str__(self):
        return f"{self.title} ({self.date})"