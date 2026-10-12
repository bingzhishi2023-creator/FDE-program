from django.core.validators import MaxLengthValidator
from django.db import models

class Document(models.Model):
    title = models.CharField("标题", max_length=160)
    text = models.TextField("正文", validators=[MaxLengthValidator(5000)])
    active = models.BooleanField("当前有效", default=True)

    class Meta:
        verbose_name = "文档"
        verbose_name_plural = "文档"

    def __str__(self):
        return self.title
