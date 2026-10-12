"""将贯穿案例的全员资料导入 Django；财务内部资料不进入此管理员演示。"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from knowledge.models import Document


class Command(BaseCommand):
    help = "导入青禾报销助手的两份公开教学制度，不导入财务内部资料"

    def handle(self, *args, **options):
        path = Path(__file__).resolve().parents[4] / "sample-documents.csv"
        count = 0
        with transaction.atomic(), path.open(encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                if row["department"].strip() != "all":
                    continue
                Document.objects.update_or_create(
                    title=row["title"].strip(),
                    defaults={"text": row["text"].strip(), "active": row["active"].strip() == "1"},
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"导入/更新 {count} 份全员教学资料；财务内部资料未导入。"))
