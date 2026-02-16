from django.contrib import admin

from apps.blog.models import Category, Tags, Post, Comments

admin.site.site_header = "Blog Admin"
admin.site.site_title = "Blog Admin Portal"
admin.site.index_title = "Welcome to the Blog Admin Portal"

admin.site.register(Category)
admin.site.register(Tags)
admin.site.register(Post)
admin.site.register(Comments)