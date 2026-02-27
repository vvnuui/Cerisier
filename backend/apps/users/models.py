from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [("admin", "Admin"), ("visitor", "Visitor")]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="visitor")
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username
