import requests

BASE_URL = "http://localhost:8001"
session_token = None


def print_menu():
    print("\n========== Auth Service ==========")
    print("1. Зарегистрироваться")
    print("2. Войти")
    print("3. Обновить токен")
    print("4. Деактивировать пользователя по ID")
    print("5. Запросить сброс пароля")
    print("6. Сбросить пароль по токену")
    print("7. Получить пользователя по ID")
    print("8. Получить список пользователей")
    print("0. Выход")
    print("==================================")


def register():
    print("\n--- Регистрация ---")
    username = input("Имя пользователя: ").strip()
    email = input("Email: ").strip()
    password = input("Пароль: ").strip()
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    if resp.status_code == 201:
        data = resp.json()
        print(f"✅ Зарегистрирован: id={data['id']}, username={data['username']}, email={data['email']}")
    else:
        print(f"❌ Ошибка: {resp.json().get('detail')}")


def login():
    global session_token
    print("\n--- Вход ---")
    username = input("Имя пользователя: ").strip()
    password = input("Пароль: ").strip()
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password
    })
    if resp.status_code == 200:
        data = resp.json()
        session_token = data['token']
        print(f"✅ Вход выполнен. Токен: {session_token[:30]}...")
        print(f"   Действителен до: {data['expires_at']}")
    else:
        print(f"❌ Ошибка: {resp.json().get('detail')}")


def refresh_token():
    global session_token
    print("\n--- Обновление токена ---")
    token = input(f"Токен [{session_token[:20] if session_token else ''}...]: ").strip()
    if not token and session_token:
        token = session_token
    resp = requests.post(f"{BASE_URL}/auth/refresh", json={"token": token})
    if resp.status_code == 200:
        data = resp.json()
        session_token = data['token']
        print(f"✅ Токен обновлён. Действителен до: {data['expires_at']}")
    else:
        print(f"❌ Ошибка: {resp.json().get('detail')}")


def deactivate_user():
    print("\n--- Деактивация пользователя ---")
    user_id = input("ID пользователя: ").strip()
    resp = requests.delete(f"{BASE_URL}/auth/users/{user_id}")
    if resp.status_code == 200:
        print("✅ Пользователь деактивирован")
    else:
        print(f"❌ Ошибка: {resp.json().get('detail')}")


def reset_request():
    print("\n--- Запрос сброса пароля ---")
    email = input("Email: ").strip()
    resp = requests.post(f"{BASE_URL}/auth/password/reset-request", json={"email": email})
    if resp.status_code == 200:
        print("✅ Запрос отправлен. Проверьте токен сброса.")
    else:
        print(f"❌ Ошибка: {resp.json().get('detail')}")


def reset_password():
    print("\n--- Сброс пароля ---")
    token = input("Токен сброса: ").strip()
    new_pass = input("Новый пароль: ").strip()
    resp = requests.post(f"{BASE_URL}/auth/password/reset", json={
        "token": token,
        "new_pass": new_pass
    })
    if resp.status_code == 200:
        print("✅ Пароль успешно изменён")
    else:
        print(f"❌ Ошибка: {resp.json().get('detail')}")


def get_user():
    print("\n--- Получить пользователя ---")
    user_id = input("ID пользователя: ").strip()
    resp = requests.get(f"{BASE_URL}/auth/users/{user_id}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  ID:         {data['id']}")
        print(f"  Username:   {data['username']}")
        print(f"  Email:      {data['email']}")
        print(f"  Активен:    {data['is_active']}")
        print(f"  Создан:     {data['created_at']}")
    else:
        print(f"❌ Ошибка: {resp.json().get('detail')}")


def list_users():
    print("\n--- Список пользователей ---")
    search = input("Поиск по username (Enter — пропустить): ").strip() or None
    is_active_input = input("Только активные? (y/n/Enter — все): ").strip().lower()
    is_active = True if is_active_input == 'y' else (False if is_active_input == 'n' else None)
    limit = input("Лимит [20]: ").strip()
    limit = int(limit) if limit else 20
    offset = input("Смещение [0]: ").strip()
    offset = int(offset) if offset else 0

    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search
    if is_active is not None:
        params["is_active"] = is_active

    resp = requests.get(f"{BASE_URL}/auth/users", params=params)
    if resp.status_code == 200:
        users = resp.json()
        if not users:
            print("  Пользователей не найдено.")
        for u in users:
            status = "✅" if u['is_active'] else "❌"
            print(f"  {status} [{u['id']}] {u['username']} — {u['email']}")
    else:
        print(f"❌ Ошибка: {resp.json().get('detail')}")


def main():
    actions = {
        '1': register,
        '2': login,
        '3': refresh_token,
        '4': deactivate_user,
        '5': reset_request,
        '6': reset_password,
        '7': get_user,
        '8': list_users,
    }
    while True:
        print_menu()
        choice = input("Выберите действие: ").strip()
        if choice == '0':
            print("До свидания!")
            break
        action = actions.get(choice)
        if action:
            try:
                action()
            except requests.exceptions.ConnectionError:
                print("❌ Нет подключения к серверу. Убедитесь что service.py запущен.")
        else:
            print("❌ Неверный выбор")


if __name__ == "__main__":
    main()
