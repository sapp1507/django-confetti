from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import UniqueConstraint
# from django.contrib.postgres.fields import ArrayField

class SettingCategory(models.Model):
    code = models.SlugField(unique=True, max_length=64)
    title = models.CharField(max_length=128)

    def __str__(self):
        return self.title


class SettingType(models.TextChoices):
    BOOL = 'bool', 'Логический'
    INT = 'int', 'Целое'
    FLOAT = 'float', 'Вещественное'
    STR = 'str', 'Строка'
    JSON = 'json', 'JSON'
    CHOICE = 'choice', 'Выбор'
    DATETIME = 'datetime', 'Дата/время'
    DURATION = 'duration', 'Длительность (сек.)'


class SettingDefinition(models.Model):
    """
    Описание настройки (реестр): ключ, тип, дефолт, валидаторы, категория.
    Значения как глобальные так и пользовательские
    """

    key = models.CharField(
        unique=True,
        max_length=120,
        verbose_name='Ключ настройки',
        help_text='Ключ настройки. Используется для обращения к настройке в коде',
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9_\.\-]+$',
                message='Ключ настройки может состоять из латинских букв, цифр и знака подчеркивания',
                code='invalid_key'
            )
        ]
    )
    category = models.ForeignKey(
        SettingCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Категория',
        help_text='Категория настройки',
        related_name='definitions'
    )
    type = models.CharField(
        max_length=15,
        choices=SettingType.choices,
        verbose_name='Тип',
        help_text='Тип настройки'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
        help_text='Описание настройки'
    )
    default = models.JSONField(null=True, blank=True, default=[])
    choices = models.JSONField(
        null=True,
        blank=True,
        default=[],
        help_text='Список объектов, у объекта ключ value обязателен, этот ключ храниться в default в виде списка'
    )
    required = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    editable = models.BooleanField(default=True)
    frontend = models.BooleanField(default=False)

    class Meta:
        ordering = ['key']

    def __str__(self):
        return self.key


class SettingScope(models.TextChoices):
    GLOBAL = 'global', 'Глобальная'
    USER = 'user', 'Пользовательская'


class SettingValue(models.Model):
    """
    Конкретное значение настройки и скопа (глобально или пользователя).
    """

    definition = models.ForeignKey(
        SettingDefinition,
        on_delete=models.CASCADE,
        verbose_name='Настройка',
        help_text='Настройка',
        related_name='values'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Пользователь',
        help_text='Пользователь',
        related_name='settings'
    )
    scope = models.CharField(
        max_length=15,
        choices=SettingScope.choices,
        verbose_name='scope',
        help_text='scope настройки'
    )
    value = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['definition', 'scope', 'user'], name='unique_setting_value')
        ]

    def __str__(self):
        user_part = self.user_id if self.user_id is not None else '-'
        return f'{self.definition.key} [{self.scope} {user_part}]'
