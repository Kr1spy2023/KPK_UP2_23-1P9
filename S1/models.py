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
    """Основная сущность: пользователь системы.
    Поле pass_hash хранит хэш пароля (входящий параметр password
    хэшируется на уровне сервиса перед сохранением)."""
    id = AutoField(primary_key=True)
    username = CharField(max_length=50, unique=True, constraints=[
        Check("length(username) >= 3"),
        Check("username GLOB '[a-z0-9_]*'")
    ])
    # Валидация формата email обеспечивается через EmailStr в сервисе
    email = CharField(max_length=100, unique=True)
    pass_hash = CharField(max_length=256)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'users'

    @classmethod
    def soft_delete(cls, user_id):
        """Деактивировать пользователя по ID.
        Возвращает True если деактивировано, иначе False."""
        updated = cls.update(is_active=False).where(
            (cls.id == user_id) & (cls.is_active == True)
        ).execute()
        return bool(updated > 0)

    @classmethod
    def get_list(cls, is_active=None, search=None, limit=20, offset=0):
        """Получить список пользователей с фильтрами is_active, search, limit, offset."""
        query = cls.select()
        if is_active is not None:
            query = query.where(cls.is_active == is_active)
        if search:
            query = query.where(cls.username.contains(search.lower()))
        return list(query.limit(limit).offset(offset))


class Token(BaseModel):
    """Токены доступа и сброса пароля.
    token_type: 'access' — срок 24 часа, 'reset' — срок 1 час.
    При создании нового токена старый того же типа аннулируется.
    Уникальный индекс (user, token_type) гарантирует один токен каждого типа."""
    id = AutoField(primary_key=True)
    user = ForeignKeyField(User, backref='tokens', on_delete='CASCADE')
    # null=False + Check гарантируют непустоту токена
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
        """Создать токен для пользователя, аннулировав предыдущий того же типа.
        access — 24 часа, reset — 1 час."""
        import secrets
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
    def reset_password(cls, token_str: str, new_pass_hash: str):
        """Сбросить пароль по токену сброса. Возвращает True при успехе."""
        token = cls.get_or_none(
            (cls.token == token_str) & (cls.token_type == 'reset')
        )
        if not token or not token.is_valid:
            return False
        User.update(pass_hash=new_pass_hash).where(
            User.id == token.user_id
        ).execute()
        token.delete_instance()
        return True


def init_db():
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