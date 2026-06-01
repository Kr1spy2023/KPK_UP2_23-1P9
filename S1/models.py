from datetime import datetime, timedelta
import secrets
from peewee import (
    SqliteDatabase, Model, AutoField, CharField,
    DateTimeField, BooleanField, ForeignKeyField, Check
)

db = SqliteDatabase('auth.db', pragmas={'case_sensitive_like': False})


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    """Основная сущность: пользователь системы.
    username и email нормализуются к нижнему регистру перед сохранением.
    pass_hash — хэш пароля; хэширование выполняется в сервисе перед вызовом create."""
    id = AutoField(primary_key=True)
    username = CharField(max_length=50, unique=True, constraints=[
        Check("length(username) >= 3"),          # минимум 3 символа
        Check("length(username) > 0"),           # не пустой
        Check("username GLOB '[a-z0-9_]*'")      # только a-z, 0-9, _
    ])
    email = CharField(max_length=100, unique=True, constraints=[
        Check("email LIKE '%@%.%'"),             # базовый формат email
        Check("length(email) > 0")              # не пустой
    ])
    pass_hash = CharField(max_length=256, constraints=[
        Check("length(pass_hash) > 0")          # не пустой
    ])
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'users'

    @classmethod
    def create_user(cls, username: str, email: str, pass_hash: str):
        """Создать пользователя с нормализацией username и email к нижнему регистру."""
        return cls.create(
            username=username.lower(),
            email=email.lower(),
            pass_hash=pass_hash
        )

    @classmethod
    def soft_delete(cls, user_id):
        """Деактивировать пользователя по ID.
        Возвращает True если деактивировано,
        False если не найден или уже деактивирован."""
        updated = cls.update(is_active=False).where(
            (cls.id == user_id) & (cls.is_active == True)
        ).execute()
        return bool(updated > 0)

    @classmethod
    def get_list(cls, is_active=None, search=None, limit=20, offset=0):
        """Получить список пользователей с фильтрами.
        Поиск по username — частичное совпадение без учёта регистра
        (SQLite настроен через case_sensitive_like=False, поиск по нижнему регистру)."""
        query = cls.select()
        if is_active is not None:
            query = query.where(cls.is_active == is_active)
        if search:
            # username хранится в нижнем регистре, поиск тоже нормализован
            query = query.where(cls.username.contains(search.lower()))
        return list(query.limit(limit).offset(offset))


class Token(BaseModel):
    """Токены доступа и сброса пароля.
    token_type: 'access' — срок 24 часа, 'reset' — срок 1 час.
    При создании нового токена старый того же типа аннулируется.
    Уникальный индекс (user, token_type) — один токен каждого типа на пользователя."""
    id = AutoField(primary_key=True)
    user = ForeignKeyField(User, backref='tokens', on_delete='CASCADE')
    token = CharField(max_length=512, null=False,
                      constraints=[Check("length(token) > 0")])
    token_type = CharField(max_length=20, constraints=[
        Check("token_type IN ('access', 'reset')")
    ])
    expires_at = DateTimeField()
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'tokens'
        indexes = (
            (('user', 'token_type'), True),
        )

    @property
    def is_valid(self):
        """Проверить, что токен не истёк."""
        return self.expires_at > datetime.now()

    @classmethod
    def create_for_user(cls, user, token_type: str):
        """Создать токен для активного пользователя, аннулировав предыдущий того же типа.
        access — 24 часа, reset — 1 час."""
        if not user.is_active:
            raise ValueError("Нельзя создать токен для деактивированного пользователя")
        hours = 24 if token_type == 'access' else 1
        cls.delete().where(
            (cls.user == user) & (cls.token_type == token_type)
        ).execute()
        return cls.create(
            user=user,
            token=secrets.token_urlsafe(64),
            token_type=token_type,
            expires_at=datetime.now() + timedelta(hours=hours)
        )

    @classmethod
    def request_reset(cls, email: str):
        """Запросить сброс пароля по email.
        Всегда возвращает True (не раскрывает наличие аккаунта)."""
        user = User.get_or_none(User.email == email.lower())
        if user and user.is_active:
            cls.create_for_user(user, 'reset')
        return True

    @classmethod
    def reset_password(cls, token_str: str, new_pass_hash: str):
        """Сбросить пароль по токену сброса.
        Возвращает True при успехе, False если токен недействителен или истёк.
        Обновление пароля и удаление токена выполняются атомарно."""
        token = cls.get_or_none(
            (cls.token == token_str) & (cls.token_type == 'reset')
        )
        if not token or not token.is_valid:
            return False
        with db.atomic():
            User.update(pass_hash=new_pass_hash).where(
                User.id == token.user_id
            ).execute()
            token.delete_instance()
        return True


def init_db():
    db.connect()
    db.create_tables([User, Token], safe=True)

    if not User.select().exists():
        User.create_user(
            username='admin',
            email='admin@example.com',
            pass_hash='hashed_password_here'
        )


if __name__ == '__main__':
    init_db()
    print("База данных auth.db успешно инициализирована.")