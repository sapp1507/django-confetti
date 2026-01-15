import icecream
from icecream import install
from pathlib import Path

install()
ic.configureOutput(includeContext=True)

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-+y+hedn+d=k#y9i&oo0kn=!6)6)stfavdp4v@1990byv=515!d'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'confetti',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CONFETTI = {
    'SEED_CATEGORIES': [
        {'code': 'main', 'title': 'Планировщик'},
        {'code': 'frontend', 'title': 'Настройки для фронта'},
        {'code': 'backend', 'title': 'Настройки для бэка'},
        {'code': 'scheduler', 'title': 'Планировщик'},
    ], # [{'code': 'scheduler', 'title': 'Планировщик'}]
    'SEED_DEFINITIONS': [
        {
            'key': 'celery.send_email',
            'type': 'bool',
            'category': 'backend',
            'title':  'Отправлять почту через celery',
            'description': 'При включенной настройки, вся почта будет отправляться через celery',
            'default': True,
            'editable': False,
        },
        {
            'key': 'test',
            'type': 'bool',
            'category': 'backend',
            'title':  'Тестовая настройка',
            'description': 'Тестовая настройка',
            'default': True,
            'editable': False,
        },
        {
            'key': 'front',
            'type': 'bool',
            'category': 'frontend',
            'title': 'Тест настройки фронта',
            'description': 'Настройка для тестирования',
            'default': True,
            'editable': False,
            'frontend': True
        },
        {
            'key': 'list',
            'type': 'choices',
            'category': 'backend',
            'title': 'Тест списка',
            'description': 'Для тестирования мультивыбора',
            'default': [
                {
                    'key': 'admin',
                    'title': 'Администратор',
                    'value': 1
                },
            ],
            'editable': False,
            'frontend': True,
            'choices': [
                {
                    'key': 'admin',
                    'title': 'Администратор',
                    'value': 1
                },
                {
                    'key': 'org_admin',
                    'title': 'Администратор организации',
                    'value': 2
                }
            ]
        },
    ],
    # {
    #     'key': 'str',
    #     'category': ForeignKey(SettingCategory),
    #     'type': SettingType.choices,
    #     'title': ChaField,
    #     'description': TextField,
    #     'default': JSONFiled,
    #     'choices': JSONField,
    #     'required': False,
    #     'enabled': True,
    #     'editable': True,
    #     'frontend': False,
    # },
}
