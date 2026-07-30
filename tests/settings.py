SECRET_KEY = 'test-secret'
DEBUG = True

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.messages',
    'confetti',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'tests.urls'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'confetti-tests',
    },
}

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

CONFETTI = {
    'AUTO_SEED': True,
    'SEED_CATEGORIES': [
        {'code': 'scheduler', 'title': 'Планировщик'},
        {'code': 'ui', 'title': 'Интерфейс'},
    ],
    'SEED_DEFINITIONS': [
        {
            'key': 'feature.jobs',
            'type': 'bool',
            'category': 'scheduler',
            'title': 'Jobs',
            'default': True,
        },
        {
            'key': 'edit',
            'type': 'bool',
            'category': 'ui',
            'title': 'Edit',
            'default': False,
            'editable': False,
        },
        {
            'key': 'front',
            'type': 'bool',
            'category': 'ui',
            'title': 'Front',
            'default': True,
            'frontend': True,
        },
        {
            'key': 'ui.theme',
            'type': 'choice',
            'category': 'ui',
            'title': 'Theme',
            'default': 'light',
            'choices': [
                {'value': 'light', 'label': 'Light'},
                {'value': 'dark', 'label': 'Dark'},
            ],
        },
    ],
}
