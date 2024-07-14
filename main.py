import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
from dotenv import load_dotenv

API_URL = "https://deckofcardsapi.com/api/deck"
IMAGE_URL = "https://raw.githubusercontent.com/crobertsbmw/deckofcards/master/static/img/"

class BlackJackBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.deck_id = None
        self.player_hand = []
        self.dealer_hand = []

    async def start(self, update: Update, context: CallbackContext):
        await update.message.reply_text("Добро пожаловать в игру BlackJack! Введите /newgame, чтобы начать новую игру.")

    async def new_game(self, update: Update, context: CallbackContext):
        response = requests.get(f"{API_URL}/new/shuffle/?deck_count=1")
        self.deck_id = response.json()['deck_id']
        self.player_hand = []
        self.dealer_hand = []

        await self.deal_card(update, context, self.player_hand, 2)
        await self.deal_card(update, context, self.dealer_hand, 2)

        await self.show_hand(update.message, context, self.player_hand, "Ваши карты: ")

        await self.send_card_image(update.message, self.dealer_hand[0])

        keyboard = [
            [InlineKeyboardButton("Еще карту", callback_data='hit')],
            [InlineKeyboardButton("Хватит", callback_data='stand')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите действие:', reply_markup=reply_markup)

    async def deal_card(self, update: Update, context: CallbackContext, hand, count=1):
        response = requests.get(f"{API_URL}/{self.deck_id}/draw/?count={count}")
        hand.extend(response.json()['cards'])

    async def show_hand(self, message, context: CallbackContext, hand, text):
        await message.reply_text(text)
        for card in hand:
            await self.send_card_image(message, card)

    async def send_card_image(self, message, card):
        card_code = card['code']
        image_url = f"{IMAGE_URL}{card_code}.png"
        await message.reply_photo(image_url)

    async def hit(self, update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()

        await self.deal_card(update, context, self.player_hand, 1)
        await self.show_hand(query.message, context, self.player_hand, "Ваши карты: ")

        if self.calculate_score(self.player_hand) > 21:
            await query.edit_message_text(text="Вы проиграли! Введите /newgame, чтобы сыграть снова.")
        else:
            await self.ask_action(query.message, context)

    async def stand(self, update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()

        dealer_score = self.calculate_score(self.dealer_hand)
        while dealer_score < 17:
            await self.deal_card(update, context, self.dealer_hand, 1)
            dealer_score = self.calculate_score(self.dealer_hand)

        player_score = self.calculate_score(self.player_hand)
        dealer_final_hand = ", ".join([f"{card['value']} {card['suit']}" for card in self.dealer_hand])
        result_message = f"Карты дилера: {dealer_final_hand}\n"

        if dealer_score > 21 or player_score > dealer_score:
            result_message += "Вы выиграли! Введите /newgame, чтобы сыграть снова."
        elif player_score < dealer_score:
            result_message += "Дилер выиграл! Введите /newgame, чтобы сыграть снова."
        else:
            result_message += "Ничья! Введите /newgame, чтобы сыграть снова."

        await query.edit_message_text(text=result_message)

    async def ask_action(self, message, context: CallbackContext):
        keyboard = [
            [InlineKeyboardButton("Еще карту", callback_data='hit')],
            [InlineKeyboardButton("Хватит", callback_data='stand')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text('Выберите действие:', reply_markup=reply_markup)

    def calculate_score(self, hand):
        values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'JACK': 10, 'QUEEN': 10, 'KING': 10, 'ACE': 11}
        score = sum([values[card['value']] for card in hand])
        aces = sum([card['value'] == 'ACE' for card in hand])

        while score > 21 and aces:
            score -= 10
            aces -= 1

        return score

    def run(self):
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('newgame', self.new_game))
        self.application.add_handler(CallbackQueryHandler(self.hit, pattern='hit'))
        self.application.add_handler(CallbackQueryHandler(self.stand, pattern='stand'))

        self.application.run_polling()

if __name__ == '__main__':
    load_dotenv()
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = BlackJackBot(TOKEN)
    bot.run()


