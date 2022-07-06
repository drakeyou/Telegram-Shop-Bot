import random
from datetime import datetime

import pymysql.cursors
import openpyxl
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.utils.exceptions import MessageTextIsEmpty
from aiogram.utils.markdown import hbold
import zlib

from config import BOT_TOKEN, HOST, PORT, USER, PASSWORD, DB_NAME, DEFAULT_PARSE_MODE, SUPPORT_USERNAME, SHOP_NAME, \
    ADMIN_ID, CREATION_TIME, CHANNEL_LINK, RULES
from qiwi import QIWIManager

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())
QIWI = QIWIManager()


def connect(db_name=None):
    try:
        connection_ = pymysql.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )

        print("Connection Successful")
        return connection_
    except Exception as err:
        print("Connection was failed")
        print(err)


def get_data_from_xlsx(file_path):
    document = openpyxl.load_workbook(file_path).active
    data = []
    for row in document.rows:
        temp = []
        for cell in row:
            temp.append(cell.value)
        data.append(temp)

    del data[0]
    return data


connection = connect(DB_NAME)
cursor = connection.cursor()

main_keyboard = ReplyKeyboardMarkup(row_width=2, keyboard=[
    [
        KeyboardButton("Купить товар"),
        KeyboardButton("Наличие товара")
    ],
    [
        KeyboardButton("Профиль"),
        KeyboardButton("О магазине")
    ],
    [
        KeyboardButton("Правила"),
        KeyboardButton("Помощь")
    ]
], resize_keyboard=True)
admin_inline_keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
    [InlineKeyboardButton("Добавить товар", callback_data="add_product")],
    [InlineKeyboardButton("Обновить товар", callback_data="update_product")],
    [InlineKeyboardButton("Удалить товар", callback_data="delete_product")],
    [InlineKeyboardButton("Удалить весь товар", callback_data="delete_all_products")]
])


class States(StatesGroup):
    add_product = State()

    change_category = State()
    change_name = State()
    change_description = State()
    change_price = State()
    change_amount = State()
    change_content = State()

    qiwi = State()


@dp.message_handler(text="Купить товар")
async def buy_product(message: types.Message):
    cursor.execute(f"SELECT category FROM `products`")
    categories = cursor.fetchall()
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
        [InlineKeyboardButton(text=categories[i]["category"], callback_data=f"buy_product_{categories[i]['category']}")]
        for i in range(len(categories))
    ])
    await message.reply(text=f"{hbold('Активные категории в магазине:')}", reply_markup=keyboard,
                        parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text_startswith='buy_product')
async def but_product(callback_data: types.CallbackQuery):
    _, _, category = callback_data.data.split("_")
    cursor.execute(f"SELECT * from `products` WHERE category='{category}'")
    products_data = cursor.fetchall()
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{products_data[i][name]} | {products_data[i][price]} ₽ | Кол-во: {str(products_data[i][amount]) + ' шт' if products_data[i][amount] > 0 else '0 шт'}.",
            callback_data=f"b_{products_data[i][name]}_{products_data[i][category_]}")]
        for i in range(len(products_data)) for _, category_, name, _, price, amount, _ in products_data
    ])
    keyboard.add(InlineKeyboardButton(f"Назад ко всем категориям", callback_data="back_to_all"))
    await callback_data.message.edit_text(text=f"{hbold('Доступные товары в разделе ' + category + ' :')}",
                                          reply_markup=keyboard,
                                          parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text="back_to_all")
async def back_to_all(callback_query: types.CallbackQuery):
    cursor.execute(f"SELECT category FROM `products`")
    categories = cursor.fetchall()
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
        [InlineKeyboardButton(text=categories[i]["category"], callback_data=f"buy_product_{categories[i]['category']}")]
        for i in range(len(categories))
    ])
    await callback_query.message.edit_text(text=f"{hbold('Активные категории в магазине:')}", reply_markup=keyboard,
                                           parse_mode=DEFAULT_PARSE_MODE)

@dp.callback_query_handler(text_startswith="back_")
async def go_back(callback_data: types.CallbackQuery):
    _, category = callback_data.data.split("_")
    cursor.execute(f"SELECT * from `products` WHERE category='{category}'")
    products_data = cursor.fetchall()
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{products_data[i][name]} | {products_data[i][price]} ₽ | Кол-во: {str(products_data[i][amount]) + ' шт' if products_data[i][amount] > 0 else '0 шт'}.",
            callback_data=f"b_{products_data[i][name]}_{products_data[i][category_]}")]
        for i in range(len(products_data)) for _, category_, name, _, price, amount, _ in products_data
    ])
    keyboard.add(InlineKeyboardButton(f"Назад ко всем категориям", callback_data="back_to_all"))
    await callback_data.message.edit_text(text=f"{hbold('Доступные товары в разделе ' + category + ' :')}",
                                          reply_markup=keyboard,
                                          parse_mode=DEFAULT_PARSE_MODE)

@dp.callback_query_handler(text_startswith='b_')
async def but_product_data(callback_data: types.CallbackQuery):
    _, name, category = callback_data.data.split("_")
    cursor.execute(f"SELECT description from `products` WHERE name='{name}' AND category='{category}' AND id=1")
    descr = dict(cursor.fetchone())["description"]
    cursor.execute(f"SELECT amount from `products` WHERE name='{name}' AND category='{category}' AND id=1")
    amount = dict(cursor.fetchone())["amount"]
    cursor.execute(f"SELECT price from `products` WHERE name='{name}' AND category='{category}' AND id=1")
    price = dict(cursor.fetchone())["price"]

    keyboard = [
        [InlineKeyboardButton(str(i + 1), callback_data=f"pc_{category}_{name}_{i + 1}_{price}") for i
         in range(int(amount))],
        [InlineKeyboardButton(f"Назад", callback_data=f"back_{category}")],
        [InlineKeyboardButton(f"Назад ко всем категориям", callback_data=f"back_to_all")]]

    text = f"📃 {hbold('Товар')}: {name}\n💰 {hbold('Цена')}: {price} ₽\n📃 {hbold('Описание')}: {descr}"
    await callback_data.message.edit_text(text,
                                          reply_markup=InlineKeyboardMarkup(row_width=5, inline_keyboard=keyboard),
                                          parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text_startswith='pc_')
async def but_processing(callback_data: types.CallbackQuery):
    _, category, name, amount, price = callback_data.data.split("_")
    cursor.execute(f"SELECT description from `products` WHERE name='{name}' AND category='{category}' AND id=1")
    descr = dict(cursor.fetchone())["description"]

    text = f"📃 {hbold('Товар')}: {name}\n💰 {hbold('Цена')}: {price} ₽\n📃 {hbold('Описание')}: {descr}"

    await callback_data.message.edit_text(text, reply_markup=InlineKeyboardMarkup(row_width=1, inline_keyboard=[
        [InlineKeyboardButton(f"QIWI", callback_data=f"qw_{amount}_{name}_{category}")],
        [InlineKeyboardButton(f"Назад", callback_data=f"back_{category}")]
    ]), parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text_startswith='qw_')
async def qiwi(callback_data: types.CallbackQuery):
    _, amount, name, category = callback_data.data.split("_")
    user_id = callback_data.from_user.id
    bill_id = random.randint(1, 9999999)
    cursor.execute(f"SELECT content from `products` WHERE name='{name}' AND category='{category}' AND id=1")
    content = dict(cursor.fetchone())["content"]
    cursor.execute(f"SELECT price from `products` WHERE name='{name}' AND category='{category}' AND id=1")
    price = dict(cursor.fetchone())["price"]
    cursor.execute(
        "INSERT INTO `purchases`(user_id, bill_id, content, product_category, product_name, paid) VALUES (%s, %s, %s ,%s, %s, %s)",
        (user_id, bill_id, content, category, name, False))
    connection.commit()

    bill = await QIWI.create_payment(amount=int(amount) * price,
                                     comment=f"{user_id}_{bill_id}")

    products_markup = InlineKeyboardMarkup(row_width=3, inline_keyboard=[
        [InlineKeyboardButton(f"Перейти к оплате", url=bill.pay_url)],
        [InlineKeyboardButton(f"Проверить оплату",
                              callback_data=f"check_{bill_id}_{user_id}_{amount}")],
        [InlineKeyboardButton(f"Отменить заказ", callback_data=f"cancelPayment_{bill_id}")],
    ])
    text = f"➖➖➖➖➖➖➖➖➖➖➖➖\n" \
           f"📃 {hbold('Товар')}: {name}\n" \
           f"💰 {hbold('Цена')}: {1} ₽\n" \
           f"📦 {hbold('Кол - во')}: {amount} шт.\n" \
           f"💡 {hbold('Заказ')}: {bill_id}\n" \
           f"🕐 {hbold('Время заказа')}: {datetime.now().strftime('%D %H:%M:%S')}\n" \
           f"🕐 {hbold('Итоговая сумма')}: {int(amount) * price} ₽\n" \
           f"💲 {hbold('Способ оплаты')}: QIWI\n" \
           f"➖➖➖➖➖➖➖➖➖➖➖➖\n" \
           f"{hbold('Перейдите по кнопке для оплаты')}\n" \
           f"➖➖➖➖➖➖➖➖➖➖➖➖"

    await callback_data.message.edit_text(text=text, reply_markup=products_markup, parse_mode=DEFAULT_PARSE_MODE)

@dp.callback_query_handler(text_startswith='cancelPayment_')
async def cancelPayment(callback_data: types.CallbackQuery):
    _, bill_id = callback_data.data.split("_")
    text = f"Платеж с уникальным идентификатором : #{bill_id} был отменен"
    await callback_data.message.answer(text)
    await callback_data.message.delete()

@dp.callback_query_handler(text_startswith="check_")
async def check_payment(callback_data: types.CallbackQuery):
    _, bill_id, user_id, amount = callback_data.data.split("_")

    cursor.execute(f"SELECT * from `purchases` WHERE bill_id={bill_id} AND user_id={user_id}")
    purchases = dict(cursor.fetchone())
    if len(purchases) > 0:
        if await QIWI.check_payment(f"{user_id}_{bill_id}") == QIWI.paid:
            cursor.execute(f"SELECT * from `users` WHERE user_id={user_id}")
            user = dict(cursor.fetchone())
            purchases_ = user["purchases"]

            content = purchases["content"].split(";")
            output = ";".join([content[i] for i in range(0, int(amount))])
            for i in range(0, int(amount)):
                del content[0]

            content = ';'.join(content)
            cursor.execute(
                f"UPDATE `purchases` SET paid=True, content='{output}' WHERE user_id={user_id} AND bill_id={bill_id}")
            connection.commit()
            cursor.execute(
                f"UPDATE `products` SET amount={len(purchases['content'].split(';')) - int(amount)}, content='{content}' WHERE category='{purchases['product_category']}' AND name='{purchases['product_name']}' AND id=1")
            connection.commit()
            cursor.execute(f"UPDATE `users` SET purchases={purchases_ + 1} WHERE user_id={user_id}")
            connection.commit()
            await callback_data.message.edit_text(f"Заказ номер #{bill_id}\n" + '\n'.join(o for o in output.split(';')))
        else:
            await callback_data.message.answer("Оплатите товар")


@dp.message_handler(text="Наличие товара")
async def products_in_store(message: types.Message):
    cursor.execute("SELECT * from `products`")
    products = cursor.fetchall()

    categories = {products[i][category]: [] for i in range(len(products)) for _, category, _, _, _, _, _ in products}
    for product in products:
        product = dict(product)
        categories[product["category"]].append([product["name"], product["price"], product["amount"]])

    text = []
    for key in categories.keys():
        text.append(f"➖➖➖ {key} ➖➖➖\n")
        for product in categories[key]:
            product_name, price, amount = product
            text.append(f"{hbold(product_name)} | {hbold(price)} ₽ | {hbold(amount)}  шт.\n")
        text.append("\n\n")
    try:
        await message.reply(text="".join(text), parse_mode=DEFAULT_PARSE_MODE)
    except MessageTextIsEmpty:
        await message.reply(text="Весь товар закончился, приносим сови извинения", parse_mode=DEFAULT_PARSE_MODE)


@dp.message_handler(text="Профиль")
async def profile(message: types.Message):
    cursor.execute(f"SELECT * from `users` WHERE user_id={message.from_user.id}")
    user_data = dict(cursor.fetchone())
    text = f"❤ {hbold('Пользователь')}: @{user_data['username'] if user_data['username'] is not None else 'Неизвестно'}\n" \
           f"💸 {hbold('Количество покупок')}: {user_data['purchases'] if user_data['purchases'] is not None else 'Неизвестно'}\n" \
           f"🔑 {hbold('ID')}: {user_data['id'] if user_data['id'] is not None else 'Неизвестно'}"

    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
        [InlineKeyboardButton("История заказов", callback_data="history")],
    ])
    await message.reply(text=text, reply_markup=keyboard, parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text='history')
async def show_history(callback_data: types.CallbackQuery):
    cursor.execute(f"SELECT * from `purchases` WHERE user_id={callback_data.from_user.id}")
    purchases_data = cursor.fetchall()
    print(purchases_data)
    if len(purchases_data) <= 0:
        await callback_data.message.reply(text=f"{hbold('Вы еще не совершали покупок :(')}",
                                          parse_mode=DEFAULT_PARSE_MODE)
    else:
        keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
            [InlineKeyboardButton(text=f"#{purchases_data[i]['bill_id']}",
                                  callback_data=f"show-history-{purchases_data[i]['bill_id']}-{purchases_data[i]['content']}")]
            for i in range(len(purchases_data))
        ])
        await callback_data.message.reply(text=f"{hbold('Ваши покупки:')}", reply_markup=keyboard,
                                          parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text_startswith='show-history')
async def show_history_products(callback_data: types.CallbackQuery):
    _, _, bill_id, content = callback_data.data.split("-")
    cursor.execute(f"SELECT paid from `purchases` WHERE user_id={callback_data.from_user.id} AND bill_id={bill_id}")
    paid = dict(cursor.fetchone())["paid"]

    if paid:
        await callback_data.message.reply(text=f"{hbold('Ваша покупка #' + bill_id + ' :')}\n{content}",
                                          parse_mode=DEFAULT_PARSE_MODE)
    else:
        await callback_data.message.reply(text=f"{hbold('Этот товар еще не оплачен')}", parse_mode=DEFAULT_PARSE_MODE)


@dp.message_handler(text="О магазине")
async def about(message: types.Message):
    text = f"🏠 {hbold('Магазин')}: {SHOP_NAME}\n" \
           f"⏰ {hbold('Дата создания')}: {CREATION_TIME}\n" \
           f"📢 {hbold('Канал')}:  Посмотреть ({CHANNEL_LINK})"
    await message.reply(text=text, parse_mode=DEFAULT_PARSE_MODE)


@dp.message_handler(text="Правила")
async def rules(message: types.Message):
    text = f"{hbold('Правила магазина:')}\n\n" + RULES
    await message.reply(text=text, parse_mode=DEFAULT_PARSE_MODE)


@dp.message_handler(text="Помощь")
async def help_manager(message: types.Message):
    await message.reply(text=f"{hbold('За помощью обращаться к')} - " + SUPPORT_USERNAME,
                        parse_mode=DEFAULT_PARSE_MODE)


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    if cursor.execute(f"SELECT * FROM `users` WHERE user_id={message.from_user.id}") == 0:
        cursor.execute(f"INSERT INTO `users`(user_id, username, purchases) VALUES (%s, %s, %s)",
                       (message.from_user.id, message.from_user.username, 0))
        connection.commit()

    text = f"Добро пожаловать в магазин {hbold(SHOP_NAME)}!\n\n\n" \
           f"Наличие можно посмотреть по кнопке {hbold('Наличие товара')}.\n\n" \
           f"{hbold('Саппорт')}: {SUPPORT_USERNAME}\n" \
           f"{hbold('Создатель')}: @dkhodos"
    await message.reply(text=text, reply_markup=main_keyboard, parse_mode=DEFAULT_PARSE_MODE)


@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply(f"{hbold('Выберите действие')}:",
                            reply_markup=admin_inline_keyboard, parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text='add_product')
async def add_product(callback_data: types.CallbackQuery):
    await callback_data.message.edit_text(text=f"{hbold('Скачайте файл и заполните его, затем отправьте обратно')}:",
                                          parse_mode=DEFAULT_PARSE_MODE)
    await callback_data.message.reply_document(document=open("./output.xlsx", "rb"))
    await States.add_product.set()


@dp.message_handler(state=States.add_product, content_types=[ContentType.DOCUMENT])
async def add_product_state(message: types.Message, state: FSMContext):
    await message.document.download(destination_file="./temp_products.xlsx")

    for data in get_data_from_xlsx("./temp_products.xlsx"):
        category, product_name, desciption, price, content = data
        amount = len(content.split(";"))
        cursor.execute(
            f"INSERT INTO `products`(category, name, description, price, amount, content) VALUES (%s, %s, %s, %s, %s, %s)",
            (category, product_name, desciption, price, amount, content))
        connection.commit()
    await message.answer(text=f"{hbold('Товар был успешно добавлен')}", parse_mode=DEFAULT_PARSE_MODE)
    await state.finish()


@dp.callback_query_handler(text_startswith='update_product')
async def update_product(callback_data: types.CallbackQuery):
    cursor.execute(f"SELECT * FROM `products`")
    products_data = cursor.fetchall()

    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
        [InlineKeyboardButton(text=f"{products_data[i][category]} | {products_data[i][name]}",
                              callback_data=f"ut_{products_data[i][category]}_{products_data[i][name]}")] for
        _, category, name, _, _, _, _ in products_data for i in range(len(products_data))
    ])

    await callback_data.message.edit_text(text=f"{hbold('Выберите товар который хотите обновить:')}",
                                          reply_markup=keyboard, parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text_startswith='ut_')
async def choose_updated_product(callback_data: types.CallbackQuery):
    _, category, name = callback_data.data.split("_")

    keyboard = InlineKeyboardMarkup(row_width=3, inline_keyboard=[
        [
            InlineKeyboardButton(text="Категорию", callback_data=f"chg_ctgr_{category}_{name}"),
            InlineKeyboardButton(text="Имя", callback_data=f"chg_nm_{category}_{name}"),
            InlineKeyboardButton(text="Описание", callback_data=f"chg_dscr_{category}_{name}"),
        ],
        [
            InlineKeyboardButton(text="Цену", callback_data=f"chg_pr_{category}_{name}"),
            InlineKeyboardButton(text="Содержимое", callback_data=f"chg_cnt_{category}_{name}"),
        ]
    ])
    await callback_data.message.edit_text(text=f"{hbold('Что хотите обновить:')}", reply_markup=keyboard,
                                          parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text_startswith='chg_')
async def change_updated_product(callback_data: types.CallbackQuery):
    _, action, category, name = callback_data.data.split("_")

    state = Dispatcher.get_current().current_state()
    await state.update_data(product_category=category)
    await state.update_data(product_name=name)

    if action == "ctgr":
        await callback_data.message.edit_text(text=f"{hbold('Напишите новую категорию:')}",
                                              parse_mode=DEFAULT_PARSE_MODE)
        await States.change_category.set()

    if action == "nm":
        await callback_data.message.edit_text(text=f"{hbold('Напишите новое название:')}",
                                              parse_mode=DEFAULT_PARSE_MODE)
        await States.change_name.set()

    if action == "dscr":
        await callback_data.message.edit_text(text=f"{hbold('Напишите новое описание:')}",
                                              parse_mode=DEFAULT_PARSE_MODE)
        await States.change_description.set()

    if action == "pr":
        await callback_data.message.edit_text(text=f"{hbold('Напишите новую цену товара:')}",
                                              parse_mode=DEFAULT_PARSE_MODE)
        await States.change_price.set()

    if action == "cnt":
        await callback_data.message.edit_text(text=f"{hbold('Напишите новое содержание товара:')}",
                                              parse_mode=DEFAULT_PARSE_MODE)
        await States.change_content.set()


@dp.message_handler(state=States.change_category)
async def apply_changes(message: types.Message, state: FSMContext):
    await state.update_data(new_category=message.text)
    data = await state.get_data()
    new_category = data["new_category"]
    product_category = data["product_category"]
    product_name = data["product_name"]

    cursor.execute(
        f"UPDATE `products` SET category='{new_category}' WHERE category='{product_category}' AND name='{product_name}' AND id=1;")
    connection.commit()

    await message.answer(text=f"{hbold('Категория успешно обновлена')}", reply_markup=admin_inline_keyboard,
                         parse_mode=DEFAULT_PARSE_MODE)
    await state.finish()


@dp.message_handler(state=States.change_name)
async def apply_changes(message: types.Message, state: FSMContext):
    await state.update_data(new_name=message.text)
    data = await state.get_data()
    new_name = data["new_name"]
    product_category = data["product_category"]
    product_name = data["product_name"]

    cursor.execute(
        f"UPDATE `products` SET name='{new_name}' WHERE category='{product_category}' AND name='{product_name}' AND id=1;")
    connection.commit()

    await message.answer(text=f"{hbold('Имя успешно обновлено')}", reply_markup=admin_inline_keyboard,
                         parse_mode=DEFAULT_PARSE_MODE)
    await state.finish()


@dp.message_handler(state=States.change_description)
async def apply_changes(message: types.Message, state: FSMContext):
    await state.update_data(new_decr=message.text)
    data = await state.get_data()
    new_decr = data["new_decr"]
    product_category = data["product_category"]
    product_name = data["product_name"]

    cursor.execute(
        f"UPDATE `products` SET description='{new_decr}' WHERE category='{product_category}' AND name='{product_name}' AND id=1;")
    connection.commit()

    await message.answer(text=f"{hbold('Описание успешно обновлено')}", reply_markup=admin_inline_keyboard,
                         parse_mode=DEFAULT_PARSE_MODE)
    await state.finish()


@dp.message_handler(state=States.change_price)
async def apply_changes(message: types.Message, state: FSMContext):
    await state.update_data(new_price=message.text)
    data = await state.get_data()
    new_price = data["new_price"]
    product_category = data["product_category"]
    product_name = data["product_name"]

    cursor.execute(
        f"UPDATE `products` SET price={new_price} WHERE category='{product_category}' AND name='{product_name}' AND id=1;")
    connection.commit()

    await message.answer(text=f"{hbold('Цена успешно обновлена')}", reply_markup=admin_inline_keyboard,
                         parse_mode=DEFAULT_PARSE_MODE)
    await state.finish()


# @dp.message_handler(state=States.change_amount)
# async def apply_changes(message: types.Message, state: FSMContext):
#     await state.update_data(new_amount=message.text)
#     data = await state.get_data()
#     new_amount = data["new_amount"]
#     product_category = data["product_category"]
#     product_name = data["product_name"]
#
#     cursor.execute(
#         f"UPDATE `products` SET amount={new_amount} WHERE category='{product_category}' AND name='{product_name}' AND id=1;")
#     connection.commit()
#
#     await message.answer(text=f"{hbold('Кол-во успешно обновлено')}", reply_markup=admin_inline_keyboard,
#                          parse_mode=DEFAULT_PARSE_MODE)
#     await state.finish()


@dp.message_handler(state=States.change_content)
async def apply_changes(message: types.Message, state: FSMContext):
    await state.update_data(new_content=message.text)
    data = await state.get_data()
    new_content = data["new_content"]
    product_category = data["product_category"]
    product_name = data["product_name"]
    amount = len(new_content.split(";"))

    cursor.execute(
        f"UPDATE `products` SET content='{new_content}' WHERE category='{product_category}' AND name='{product_name}' AND id=1;")
    cursor.execute(
        f"UPDATE `products` SET amount={amount} WHERE category='{product_category}' AND name='{product_name}' AND id=1;")
    connection.commit()

    await message.answer(text=f"{hbold('Содержание успешно обновлено')}", reply_markup=admin_inline_keyboard,
                         parse_mode=DEFAULT_PARSE_MODE)
    await state.finish()


@dp.message_handler(commands=["keyboard"])
async def show_keyboard(message: types.Message):
    await message.reply(text=f"{hbold('Показываю клавиатуру')}", reply_markup=main_keyboard,
                        parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text='delete_product')
async def delete_product(callback_data: types.CallbackQuery):
    cursor.execute(f"SELECT * FROM `products`")
    products_data = cursor.fetchall()
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[
        [InlineKeyboardButton(text=f"{products_data[i][category]} | {products_data[i][name]}",
                              callback_data=f"dlt_{products_data[i][category]}_{products_data[i][name]}")] for
        _, category, name, _, _, _, _ in products_data for i in range(len(products_data))
    ])

    await callback_data.message.edit_text(text=f"{hbold('Выберите товар который хотите удалить:')}",
                                          reply_markup=keyboard, parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text_startswith='dlt')
async def apply_changes(callback_data: types.CallbackQuery):
    _, category, name = callback_data.data.split("_")

    cursor.execute(f"DELETE from `products` WHERE category='{category}' and name='{name}'")
    connection.commit()

    await callback_data.message.edit_text(text=f"{hbold('Товар ' + name + ' успешно удален')}",
                                          parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text="delete_all_products")
async def delete_all_products(callback_data: types.CallbackQuery):
    cursor.execute("DELETE from `products`")
    connection.commit()

    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [
            InlineKeyboardButton(text="Уверен", callback_data="delete_answer_yes"),
            InlineKeyboardButton(text="Отменить", callback_data="delete_answer_no"),
        ]
    ])
    await callback_data.message.edit_text(text=f"{hbold('Вы уверены?')}",
                                          reply_markup=keyboard,
                                          parse_mode=DEFAULT_PARSE_MODE)


@dp.callback_query_handler(text_startswith="delete_answer")
async def delete_all_products(callback_data: types.CallbackQuery):
    _, _, answer = callback_data.data.split("_")

    if answer == "yes":
        cursor.execute("DELETE from `products`")
        connection.commit()

        await callback_data.message.edit_text(text=f"{hbold('Все товары были удалены.')}",
                                              parse_mode=DEFAULT_PARSE_MODE)
    else:
        await callback_data.message.edit_text(text=f"{hbold('Удаление отменено.')}", parse_mode=DEFAULT_PARSE_MODE)


if __name__ == '__main__':
    # register_all_message_functions(dp)
    # register_all_callback_functions(dp)

    executor.start_polling(dp, skip_updates=True)
