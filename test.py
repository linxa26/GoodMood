'''Добавляем библиотеку рэндом:
'''
import random

'''1. Создаём словари с уровнями сложности:
'''
words_easy = {
    "family": "семья",
    "hand": "рука",
    "people": "люди",
    "evening": "вечер",
    "minute": "минута"
}

words_medium = {
    "believe": "верить",
    "feel": "чувствовать",
    "make": "делать",
    "open": "открывать",
    "think": "думать"
}

words_hard = {
    "rural": "деревенский",
    "fortune": "удача",
    "vague": "расплывчатый",
    "wrestle": "бороться",
    "exhaust": "истощать"
}

levels = {
    0: 'Нулевой',
    1: 'Так себе',
    2: 'Можно лучше',
    3: 'Норм',
    4: 'Хорошо',
    5: 'Отлично'
}

'''2. Выбираем уровень сложности:)
'''


def choose_difficulty():
    print("Выберите уровень сложности.")
    print("Лёгкий, средний, сложный.")
    choice = input("Ваш выбор: ").lower()

    if choice == "лёгкий":
        return words_easy
    elif choice == "средний":
        return words_medium
    elif choice == "сложный":
        return words_hard
    else:
        print("Неверный ввод, выбран средний уровень сложности.")
        return words_medium


'''3. Логика нашей игры:
'''


def play_game(words):
    print("Выбран уровень сложности. Мы предложим 5 слов, подберите перевод.")
    answers = {}

    keys = list(words.keys())
    random.shuffle(keys)

    for word in keys:
        translation = words[word]
        first_letter = translation[0]
        length = len(translation)
        print(f"{word}, {length} букв, начинается на {first_letter}...")
        user_answer = input("Ваш ответ: ").strip().lower()

        if user_answer == translation:
            print(f"Верно. {word.capitalize()} — это {translation}.")
            answers[word] = True
        else:
            print(f"Неправильно. {word.capitalize()} — это {translation}.")
            answers[word] = False
        print()
    return answers


'''4. Выводим результаты:
'''


def display_results(answers):
    correct = [word for word, result in answers.items() if result]
    wrong = [word for word, result in answers.items() if not result]

    print("Правильно отвечены слова:")
    for word in correct:
        print(word)

    print("\nНеправильно отвечены слова:")
    for word in wrong:
        print(word)
    print()


'''5. Определяем ранг:))
'''


def calculate_rank(answers):
    correct_count = sum(answers.values())
    return (f"Ваш ранг: {levels[correct_count]}")


'''6. А теперь ракета)) - запускаем
'''


def main():
    words = choose_difficulty()
    answers = play_game(words)
    display_results(answers)
    calculate_rank(answers)
    print("Завершение программы.")


# Запуск игры
main()
