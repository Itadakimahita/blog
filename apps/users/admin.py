from django.contrib import admin

from apps.users.models import CustomUser

# Register your models here.
admin.site.site_header = "Users Admin"
admin.site.site_title = "Users Admin Portal"
admin.site.index_title = "Welcome to the Users Admin Portal"

admin.site.register(CustomUser)