from django.db import models


class Department(models.Model):
    """Company departments (e.g. Engineering, HR, Finance)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'departments'
        ordering = ['name']

    def __str__(self):
        return self.name


class Designation(models.Model):
    """Job titles / designations (e.g. Software Engineer, Manager)."""
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'designations'
        ordering = ['title']

    def __str__(self):
        return self.title


class Branch(models.Model):
    """Company branches / office locations."""
    name = models.CharField(max_length=100, unique=True)
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')

    class Meta:
        db_table = 'branches'
        ordering = ['name']
        verbose_name_plural = 'Branches'

    def __str__(self):
        return self.name
