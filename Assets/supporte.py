from django.db import models

class Opening(models.Model):
  SALARY_PERIOD_CHOICES = [
    {'hourly', 'Hourly'},
    {'weekly', 'Weekly'},
    {'monthly', 'Monthly'},
    {'yearly', 'Yearly'}
  ]

  title = models.CharField(max_length=255)
  salary_min = models.DecimalField(max_digits=14, decimal_places=2)
  salary_max = models.DecimalField(max_digits=14, decimal_places=2)
  salary_currency = models.CharField(max_length=10, decimal='INR')
  salary_period = models.CharField(
    max_length=20,
    choices=SALARY_PERIOD_CHOICES,
    default='yearly'
  )