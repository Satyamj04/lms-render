from django.apps import AppConfig


class AdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin'
    # Use a unique label to avoid colliding with Django's built-in 'admin' app
    label = 'myproject_admin'
    verbose_name = 'Project Admin'
