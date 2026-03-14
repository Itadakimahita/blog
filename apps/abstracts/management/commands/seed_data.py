from __future__ import annotations

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.blog.enums.post_status import PostStatus
from apps.blog.models import Category, Comments, Post, Tags


class Command(BaseCommand):
    help = "Seed the local SQLite database with demo users, categories, tags, posts, and comments."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--admin-email", default=None)
        parser.add_argument("--admin-password", default=None)
        parser.add_argument("--admin-first-name", default="Admin")
        parser.add_argument("--admin-last-name", default="User")
        parser.add_argument(
            "--update-admin-password",
            action="store_true",
            help="If set and the admin user exists, update its password to --admin-password.",
        )
        parser.add_argument(
            "--published-posts",
            type=int,
            default=25,
            help="How many published posts to create.",
        )
        parser.add_argument(
            "--draft-posts",
            type=int,
            default=10,
            help="How many draft posts to create.",
        )
        parser.add_argument(
            "--archived-posts",
            type=int,
            default=10,
            help="How many archived posts to create.",
        )
        parser.add_argument(
            "--comments-per-post",
            type=int,
            default=2,
            help="How many comments to create per published post.",
        )
        parser.add_argument(
            "--random-seed",
            type=int,
            default=42,
            help="Random seed for deterministic seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        random.seed(int(options["random_seed"]))

        admin_email = options["admin_email"]
        admin_password = options["admin_password"]
        admin_first_name = options["admin_first_name"]
        admin_last_name = options["admin_last_name"]
        update_admin_password = bool(options["update_admin_password"])

        User = get_user_model()

        if (admin_email and not admin_password) or (admin_password and not admin_email):
            raise SystemExit("Both --admin-email and --admin-password must be provided together.")

        if admin_email and admin_password:
            admin = User.objects.filter(email=admin_email).first()
            if admin is None:
                User.objects.create_superuser(
                    email=admin_email,
                    first_name=admin_first_name,
                    last_name=admin_last_name,
                    password=admin_password,
                )
                self.stdout.write(self.style.SUCCESS(f"Superuser created: {admin_email}"))
            else:
                changed = False
                if not getattr(admin, "is_staff", False):
                    admin.is_staff = True
                    changed = True
                if not getattr(admin, "is_superuser", False):
                    admin.is_superuser = True
                    changed = True
                if update_admin_password:
                    admin.set_password(admin_password)
                    changed = True
                if changed:
                    admin.save()
                self.stdout.write(self.style.WARNING(f"Superuser already exists: {admin_email}"))

        def get_or_create_user(email: str, first: str, last: str, lang: str, tz: str) -> object:
            user = User.objects.filter(email=email).first()
            if user is None:
                return User.objects.create_user(
                    email=email,
                    first_name=first,
                    last_name=last,
                    password="User12345!",
                    preferred_language=lang,
                    timezone=tz,
                )
            changed = False
            for field, value in {
                "first_name": first,
                "last_name": last,
                "preferred_language": lang,
                "timezone": tz,
            }.items():
                if getattr(user, field, None) != value:
                    setattr(user, field, value)
                    changed = True
            if changed:
                user.save()
            return user

        users = [
            get_or_create_user("user1@example.com", "Ivan", "Petrov", "ru", "Europe/Moscow"),
            get_or_create_user("user2@example.com", "Aruzhan", "Bek", "kk", "Asia/Almaty"),
            get_or_create_user("user3@example.com", "John", "Smith", "en", "UTC"),
            get_or_create_user("user4@example.com", "Olga", "Sidorova", "ru", "Asia/Almaty"),
            get_or_create_user("user5@example.com", "Nurs", "Aman", "kk", "UTC"),
        ]

        categories = [
            ("news", "News", "Новости", "Жаңалықтар"),
            ("tech", "Tech", "Технологии", "Технология"),
            ("life", "Life", "Жизнь", "Өмір"),
        ]
        category_objs: list[Category] = []
        for slug, en, ru, kk in categories:
            obj, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={"name_en": en, "name_ru": ru, "name_kk": kk},
            )
            changed = False
            for field, value in {"name_en": en, "name_ru": ru, "name_kk": kk}.items():
                if getattr(obj, field) != value:
                    setattr(obj, field, value)
                    changed = True
            if changed:
                obj.save()
            category_objs.append(obj)

        tags = ["django", "drf", "redis", "i18n", "python", "testing", "api", "cache"]
        tag_objs: list[Tags] = []
        for tag in tags:
            tag_slug = slugify(tag)
            obj, _ = Tags.objects.get_or_create(slug=tag_slug, defaults={"name": tag})
            if obj.name != tag:
                obj.name = tag
                obj.save(update_fields=["name"])
            tag_objs.append(obj)

        def get_or_create_post(idx: int, status: str) -> Post:
            slug = f"post-{idx:04d}"
            title = f"Demo post {idx:04d}"
            body = (
                f"This is a seeded post body for {slug}. "
                "It exists to test pagination, filtering, and localization."
            )
            author = random.choice(users)
            category = random.choice(category_objs)

            post = Post.objects.filter(slug=slug).first()
            if post is None:
                post = Post.objects.create(
                    slug=slug,
                    title=title,
                    body=body,
                    status=status,
                    author=author,
                    category=category,
                )
            else:
                changed = False
                for field, value in {
                    "title": title,
                    "body": body,
                    "status": status,
                    "author": author,
                    "category": category,
                }.items():
                    if getattr(post, field) != value:
                        setattr(post, field, value)
                        changed = True
                if changed:
                    post.save()

            post.tags.set(random.sample(tag_objs, k=random.randint(1, min(4, len(tag_objs)))))
            return post

        published_count = int(options["published_posts"])
        draft_count = int(options["draft_posts"])
        archived_count = int(options["archived_posts"])
        comments_per_post = int(options["comments_per_post"])

        published_posts = [
            get_or_create_post(i, PostStatus.PUBLISHED) for i in range(1, published_count + 1)
        ]
        for i in range(published_count + 1, published_count + draft_count + 1):
            get_or_create_post(i, PostStatus.DRAFT)
        for i in range(
            published_count + draft_count + 1,
            published_count + draft_count + archived_count + 1,
        ):
            get_or_create_post(i, PostStatus.ARCHIVED)

        for post in published_posts:
            for j in range(1, comments_per_post + 1):
                body = f"Seeded comment {j} on {post.slug}"
                author = random.choice(users)
                Comments.objects.get_or_create(post=post, author=author, body=body)

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write(f"Users: {User.objects.count()}")
        self.stdout.write(f"Categories: {Category.objects.count()}")
        self.stdout.write(f"Tags: {Tags.objects.count()}")
        self.stdout.write(f"Posts: {Post.objects.count()}")
        self.stdout.write(f"Comments: {Comments.objects.count()}")
