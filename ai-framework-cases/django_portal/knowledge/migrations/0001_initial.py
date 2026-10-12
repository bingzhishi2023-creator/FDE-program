from django.db import migrations, models
from django.core.validators import MaxLengthValidator

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.CreateModel(
        name="Document",
        fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160, verbose_name="标题")),
                ("text", models.TextField(validators=[MaxLengthValidator(5000)], verbose_name="正文")),
                ("active", models.BooleanField(default=True, verbose_name="当前有效"))],
        options={"verbose_name": "文档", "verbose_name_plural": "文档"})]
