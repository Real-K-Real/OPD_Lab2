# импорт из библиотеки aiogram
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

# необходимый для работы токен, получаемый в боте BotFather
BOT_TOKEN = ""
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# временное хранилище данных одного пользователя
current_state = {}

# функция калькулятора кредита
def calculate_credit(amount, rate, months):
    monthly_rate = rate / 12 / 100
    payment = amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    total_payment = payment * months
    overpayment = total_payment - amount
    return payment, total_payment, overpayment

# функция калькулятора кредита с досрочным погашением
def calculate_credit_early(amount, rate, months, early_payment, early_month):
    monthly_rate = rate / 12 / 100
    payment_before = amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    paid_before_early = payment_before * (early_month - 1)
    remaining_balance = amount
    for i in range(1, early_month):
        interest = remaining_balance * monthly_rate
        principal = payment_before - interest
        remaining_balance -= principal
    remaining_balance -= early_payment
    if remaining_balance <= 0:
        return payment_before, 0, paid_before_early + early_payment, paid_before_early + early_payment - amount
    remaining_months = months - (early_month - 1)
    payment_after = remaining_balance * (monthly_rate * (1 + monthly_rate) ** remaining_months) / (
                (1 + monthly_rate) ** remaining_months - 1)
    total_payment = paid_before_early + early_payment + (payment_after * remaining_months)
    overpayment = total_payment - amount
    return payment_before, payment_after, total_payment, overpayment

# функция калькулятора вкладов
def calculate_deposit(amount, rate, months, monthly_addition=0):
    monthly_rate = rate / 12 / 100
    final_amount = amount
    for _ in range(months):
        interest = final_amount * monthly_rate
        final_amount += interest + monthly_addition
    interest_earned = final_amount - amount - (monthly_addition * months)
    return final_amount, interest_earned

# кнопки на клавиатуре в сообщении
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Кредитный калькулятор", callback_data="credit"))
    builder.add(types.InlineKeyboardButton(text="Кредитный калькулятор с досрочным погашением", callback_data="credit_early"))
    builder.add(types.InlineKeyboardButton(text="Калькулятор вкладов", callback_data="deposit"))
    builder.add(types.InlineKeyboardButton(text="Игра 52 недели богатства", callback_data="wealth52"))
    builder.adjust(1)
    return builder.as_markup()
def get_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="В главное меню", callback_data="back_to_main"))
    return builder.as_markup()

# функции кнопок
@dp.callback_query(lambda c: c.data == "back_to_main")
async def process_back_to_main(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "Выберите один из доступных режимов:",
        reply_markup=get_main_keyboard()
    )
    await callback_query.answer()

@dp.message(Command("start"))
async def process_start_command(message: types.Message):
    await message.answer(
        "Добро пожаловать в Финансовый бот!\n\n"
        "Выберите один из доступных режимов:",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(lambda c: c.data in ["credit", "credit_early", "deposit", "wealth52"])
async def process_bot_selection(callback_query: types.CallbackQuery):
    bot_type = callback_query.data
    current_state.clear()
    current_state["type"] = bot_type
    current_state["step"] = 1
    if bot_type == "credit":
        await callback_query.message.edit_text(
            "Кредитный калькулятор\n\n"
            "Шаг 1: Введите сумму кредита (в рублях):"
        )
    elif bot_type == "credit_early":
        await callback_query.message.edit_text(
            "Кредитный калькулятор с досрочным погашением\n\n"
            "Шаг 1: Введите сумму кредита (в рублях):"
        )
    elif bot_type == "deposit":
        await callback_query.message.edit_text(
            "Калькулятор вкладов\n\n"
            "Шаг 1: Введите начальную сумму вклада (в рублях):"
        )
    elif bot_type == "wealth52":
        await callback_query.message.edit_text(
            "Игра 52 недели богатства\n\n"
            "Шаг 1: Введите желаемую сумму для накопления за 52 недели (в рублях):"
        )
    await callback_query.answer()

# сообщения - ответы на сообщения пользователя
@dp.message()
async def process_input(message: types.Message):
    if not current_state:
        await message.answer(
            "Пожалуйста, выберите калькулятор:",
            reply_markup=get_main_keyboard()
        )
        return
    calculator_type = current_state.get("type")
    step = current_state.get("step")
    number = float(message.text)
    try:
        if calculator_type == "credit":
            await process_credit_input(message, number, step)
        elif calculator_type == "credit_early":
            await process_credit_early_input(message, number, step)
        elif calculator_type == "deposit":
            await process_deposit_input(message, number, step)
        elif calculator_type == "wealth52":
            await process_wealth52_input(message, number, step)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")


async def process_credit_input(message: types.Message, number, step):
    if step == 1:
        current_state["amount"] = number
        current_state["step"] = 2
        await message.answer("Шаг 2: Введите годовую процентную ставку (в %):")
    elif step == 2:
        if number <= 0 or number >= 100:
            await message.answer("Процентная ставка должна быть больше 0 и меньше 100%")
            return
        current_state["rate"] = number
        current_state["step"] = 3
        await message.answer("Шаг 3: Введите срок кредита (в месяцах):")
    elif step == 3:
        if number <= 0 or not number.is_integer():
            await message.answer("Срок кредита должен быть положительным целым числом месяцев")
            return
        amount = current_state["amount"]
        rate = current_state["rate"]
        months = int(number)
        payment, total, overpayment = calculate_credit(amount, rate, months)
        result_message = (
            f"Результаты расчета кредита:\n\n"
            f"Сумма кредита: {amount:,.2f} ₽\n"
            f"Процентная ставка: {rate:.2f}%\n"
            f"Срок: {months} мес.\n\n"
            f"Ежемесячный платеж: <b>{payment:,.2f} ₽\n"
            f"Общая сумма выплат: <b>{total:,.2f} ₽\n"
            f"Переплата: <b>{overpayment:,.2f} ₽)"
        )
        current_state.clear()
        await message.answer(
            result_message,
            reply_markup=get_back_keyboard()
        )

async def process_credit_early_input(message: types.Message, number, step):
    if step == 1:
        current_state["amount"] = number
        current_state["step"] = 2
        await message.answer("Шаг 2: Введите годовую процентную ставку (в %):")
    elif step == 2:
        if number <= 0 or number >= 100:
            await message.answer("Процентная ставка должна быть больше 0 и меньше 100%")
            return
        current_state["rate"] = number
        current_state["step"] = 3
        await message.answer("Шаг 3: Введите срок кредита (в месяцах):")
    elif step == 3:
        if number <= 0 or not number.is_integer():
            await message.answer("Срок кредита должен быть положительным целым числом месяцев")
            return
        current_state["months"] = int(number)
        current_state["step"] = 4
        await message.answer("Шаг 4: Введите сумму досрочного погашения (в рублях):")
    elif step == 4:
        if number <= 0:
            await message.answer("Сумма досрочного погашения должна быть положительным числом")
            return
        current_state["early_payment"] = number
        current_state["step"] = 5
        await message.answer(f"Шаг 5: Введите месяц досрочного погашения (от 2 до {current_state['months']}):")
    elif step == 5:
        if not number.is_integer() or number < 2 or number > current_state["months"]:
            await message.answer(f"Месяц должен быть целым числом от 2 до {current_state['months']}")
            return
        amount = current_state["amount"]
        rate = current_state["rate"]
        months = current_state["months"]
        early_payment = current_state["early_payment"]
        early_month = int(number)
        payment_before, payment_after, total, overpayment = calculate_credit_early(
            amount, rate, months, early_payment, early_month
        )
        result_message = (
            f"Результаты расчета кредита с досрочным погашением:\n\n"
            f"Сумма кредита: {amount:,.2f} ₽\n"
            f"Процентная ставка: {rate:.2f}%\n"
            f"Срок: {months} мес.\n"
            f"Досрочное погашение: {early_payment:,.2f} ₽ в {early_month}-й месяц\n\n"
            f"Ежемесячный платеж до погашения: {payment_before:,.2f} ₽\n"
        )
        if payment_after > 0:
            result_message += (
                f"Ежемесячный платеж после погашения: {payment_after:,.2f} ₽\n"
                f"Снижение платежа: {payment_before - payment_after:,.2f} ₽\n"
            )
        else:
            result_message += "Кредит будет полностью погашен после досрочного погашения!\n"
        result_message += (
            f"Общая сумма выплат: {total:,.2f} ₽\n"
            f"Переплата: {overpayment:,.2f} ₽)"
        )
        current_state.clear()
        await message.answer(
            result_message,
            reply_markup=get_back_keyboard()
        )


async def process_deposit_input(message: types.Message, number, step):
    if step == 1:
        current_state["amount"] = number
        current_state["step"] = 2
        await message.answer("Шаг 2: Введите годовую процентную ставку (в %):")
    elif step == 2:
        if number <= 0 or number >= 100:
            await message.answer("Процентная ставка должна быть больше 0 и меньше 100%")
            return
        current_state["rate"] = number
        current_state["step"] = 3
        await message.answer("Шаг 3: Введите срок вклада (в месяцах):")
    elif step == 3:
        if number <= 0 or not number.is_integer():
            await message.answer("Срок вклада должен быть положительным целым числом месяцев")
            return
        current_state["months"] = int(number)
        current_state["step"] = 4
        await message.answer("Шаг 4: Введите сумму ежемесячного пополнения (0, если без пополнения):")
    elif step == 4:
        if number < 0:
            await message.answer("Сумма ежемесячного пополнения не может быть отрицательной")
            return
        amount = current_state["amount"]
        rate = current_state["rate"]
        months = current_state["months"]
        monthly_addition = number
        final_amount, interest_earned = calculate_deposit(amount, rate, months, monthly_addition)
        total_invested = amount + (monthly_addition * months)
        result_message = (
            f"Результаты расчета вклада:\n\n"
            f"Начальная сумма: {amount:,.2f} ₽\n"
            f"Процентная ставка: {rate:.2f}%\n"
            f"Срок: {months} мес.\n"
            f"Ежемесячное пополнение: {monthly_addition:,.2f} ₽\n\n"
            f"Итоговая сумма: {final_amount:,.2f} ₽\n"
            f"Внесено средств: {total_invested:,.2f} ₽\n"
            f"Начислено процентов: {interest_earned:,.2f} ₽)"
        )
        current_state.clear()
        await message.answer(
            result_message,
            reply_markup=get_back_keyboard()
        )

# из-за простоты работы, ради 52 недель богатства было принято решение не делать отдельную функцию
async def process_wealth52_input(message: types.Message, number, step):
    if step == 1:
        current_state["target"] = number
        total = current_state["target"]
        sum_ranks = 52 * 53 / 2
        factor = total / sum_ranks
        plan_lines = [f"Неделя {w}: {factor * w:,.2f} ₽" for w in range(1, 53)]
        result_msg = "План накоплений на 52 недели:\n\n" + "\n".join(plan_lines)
        current_state.clear()
        await message.answer(
            result_msg,
            reply_markup=get_back_keyboard()
        )

# asyncio для непрерывной работы программы, а соответственно и бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())