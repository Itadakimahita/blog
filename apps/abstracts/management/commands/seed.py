from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed the database with demo data."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--admin-email", default="admin@example.com")
        parser.add_argument("--admin-password", default="admin12345")
        parser.add_argument("--admin-first-name", default="Admin")
        parser.add_argument("--admin-last-name", default="User")
        parser.add_argument(
            "--no-update-admin-password",
            action="store_false",
            dest="update_admin_password",
            help="Do not update the admin password if the admin user already exists.",
        )
        parser.set_defaults(update_admin_password=True)
        parser.add_argument("--published-posts", type=int, default=25)
        parser.add_argument("--draft-posts", type=int, default=10)
        parser.add_argument("--archived-posts", type=int, default=10)
        parser.add_argument("--comments-per-post", type=int, default=2)
        parser.add_argument("--random-seed", type=int, default=42)

    def handle(self, *args, **options) -> None:
        call_command(
            "seed_data",
            admin_email=options["admin_email"],
            admin_password=options["admin_password"],
            admin_first_name=options["admin_first_name"],
            admin_last_name=options["admin_last_name"],
            update_admin_password=options["update_admin_password"],
            published_posts=options["published_posts"],
            draft_posts=options["draft_posts"],
            archived_posts=options["archived_posts"],
            comments_per_post=options["comments_per_post"],
            random_seed=options["random_seed"],
        )
