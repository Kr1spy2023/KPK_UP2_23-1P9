from datetime import datetime, timedelta
from peewee import (
    SqliteDatabase, Model, AutoField, CharField,
    DateTimeField, BooleanField, ForeignKeyField, Check
)

db = SqliteDatabase('auth.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    """Основная сущность: пользователь системы."""
    id = AutoField(primary_key=True)
    username = CharField(max_length=50, unique=True, constraints=[
        Check("length(username) >= 3"),
        Check("username GLOB '[a-z0-9_]*'")  # только a-z, 0-9, _
    ])
    email = CharField(max_length=100, unique=True)
    pass_hash = CharField(max_length=256)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'users'

    @classmethod
    def soft_delete(cls, user_id):
        """Мягкое удаление: is_active = False. Возвращает True если деактивировано, иначе False."""
        updated = cls.update(is_active=False).where(
            (cls.id == user_id) & (cls.is_active == True)
        ).execute()
        return bool(updated > 0)


class Token(BaseModel):
    """Токены доступа и сброса пароля.
    Уникальный индекс (user, token_type) гарантирует один активный токен
    каждого типа на пользователя."""
    id = AutoField(primary_key=True)
    user = ForeignKeyField(User, backref='tokens', on_delete='CASCADE')
    token = CharField(max_length=512, unique=True, null=False)
    token_type = CharField(max_length=20, constraints=[
        Check("token_type IN ('access', 'reset')")
    ])
    expires_at = DateTimeField()
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'tokens'
        indexes = (
            (('user', 'token_type'), True),  # один токен каждого типа на пользователя
        )

    @property
    def is_valid(self):
        return self.expires_at > datetime.now()


def init_db():
    """Создание таблиц и заполнение начальными данными"""
    db.connect()
    db.create_tables([User, Token], safe=True)

    if not User.select().exists():
        User.create(
            username='admin',
            email='admin@example.com',
            pass_hash='hashed_password_here'
        )


if __name__ == '__main__':
    init_db()
    print("База данных auth.db успешно инициализирована.")