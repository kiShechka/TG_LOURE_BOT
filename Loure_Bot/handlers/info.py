from aiogram.types import Message
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram import Router, F

info_router = Router()

@info_router.message(Command("ban_info"))
async def ban_info(message: Message):
    rules = [
        "❌ Не выкладывать фото содержащие NSFW контент",
        "❌ Не выкладывать откровенную обнаженку без спойлера", 
        "❌ Не выкладывать фото с проникновениями различного характера в эрогенные места",
        "❌ Не пиарить флуды и ролки",
        "❌ Не обманывать заказчиков и исполнителей",
        "❌ Не разжигать ненависть. Если в канале присутствует разжигание ненависти, анкета будет баниться",
        "❌ Не выкладывать чужие работы защищенные авторским правом",
        "✅ Если в канале присутствуют темы NSFW, просто укажите об этом в описании"
    ]
    
    text = "📋 <b>Правила публикации анкет:</b>\n\n" + "\n".join(rules)
    
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Смотреть анкеты", callback_data='view_profiles')]
        ])
    )