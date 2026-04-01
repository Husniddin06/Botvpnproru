from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    waiting_promo      = State()
    waiting_screenshot = State()


class WithdrawStates(StatesGroup):
    waiting_wallet = State()
    waiting_amount = State()


class BroadcastStates(StatesGroup):
    waiting_target  = State()
    waiting_message = State()


class AdminStates(StatesGroup):
    waiting_give_sub       = State()
    waiting_give_bal       = State()
    waiting_promo_code     = State()
    waiting_promo_discount = State()
    waiting_promo_uses     = State()


class FeedbackStates(StatesGroup):
    waiting_comment = State()
