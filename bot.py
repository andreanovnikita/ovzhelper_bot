import os
import logging
import tempfile
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from gtts import gTTS
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from io import BytesIO
import textwrap
from collections import Counter
import numpy as np
import re

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class EducationalBot:
    def __init__(self, token):
        self.token = token
        self.supported_languages = {
            'ru': 'Русский',
            'en': 'Английский', 
            'es': 'Испанский',
            'fr': 'Французский',
            'de': 'Немецкий'
        }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда начала работы с ботом"""
        # Очищаем все состояния пользователя
        context.user_data.clear()
        
        keyboard = [
            [InlineKeyboardButton("🎧 Текст в речь", callback_data="tts")],
            [InlineKeyboardButton("📊 Визуализация текста", callback_data="visualize")],
            [InlineKeyboardButton("🎮 Интерактивные задания", callback_data="interactive")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🤖 **Образовательный Бот для Доступного Обучения**

Я помогу сделать обучение доступным для всех! Выберите функцию:

🎧 **Текст в речь** - озвучка текста для слабовидящих
📊 **Визуализация текста** - создание инфографики и диаграмм
🎮 **Интерактивные задания** - игровое обучение

Выберите действие ниже 👇
        """
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "tts":
            await self.show_tts_menu(query, context)
            
        elif query.data.startswith("lang_"):
            await self.handle_language_selection(query, context)
            
        elif query.data == "visualize":
            await self.show_visualization_menu(query, context)
            
        elif query.data.startswith("viz_"):
            await self.handle_visualization_selection(query, context)
            
        elif query.data == "interactive":
            await self.show_interactive_menu(query, context)
            
        elif query.data == "help":
            await self.show_help(query, context)
            
        elif query.data == "back":
            await self.show_main_menu(query, context)

    async def show_tts_menu(self, query, context):
        """Меню текста в речь"""
        # Очищаем состояние визуализации
        context.user_data.pop('viz_type', None)
        context.user_data['mode'] = 'tts'
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
             InlineKeyboardButton("🇺🇸 Английский", callback_data="lang_en")],
            [InlineKeyboardButton("🇪🇸 Испанский", callback_data="lang_es"),
             InlineKeyboardButton("🇫🇷 Французский", callback_data="lang_fr")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🎧 **Текст в речь**\n\nВыберите язык для озвучки:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_language_selection(self, query, context):
        """Обработка выбора языка"""
        lang = query.data.split("_")[1]
        context.user_data['tts_lang'] = lang
        context.user_data['mode'] = 'tts_waiting_text'
        
        await query.edit_message_text(
            f"🎧 Выбран язык: {self.supported_languages[lang]}\n\n"
            f"Отправьте текст для преобразования в речь (максимум 1000 символов):"
        )

    async def show_visualization_menu(self, query, context):
        """Меню визуализации"""
        # Очищаем состояние TTS
        context.user_data.pop('tts_lang', None)
        context.user_data.pop('mode', None)
        context.user_data['mode'] = 'viz_choosing_type'
        
        keyboard = [
            [InlineKeyboardButton("📈 Частотный анализ", callback_data="viz_freq")],
            [InlineKeyboardButton("📊 Статистика текста", callback_data="viz_stats")],
            [InlineKeyboardButton("🎯 Круговая диаграмма", callback_data="viz_pie")],
            [InlineKeyboardButton("📋 Структура текста", callback_data="viz_structure")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
📊 **Визуализация текста**

Выберите тип инфографики:

📈 **Частотный анализ** - топ слов в тексте
📊 **Статистика текста** - основные метрики
🎯 **Круговая диаграмма** - распределение частей речи
📋 **Структура текста** - визуальное представление

Выберите вариант ниже 👇
        """
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_visualization_selection(self, query, context):
        """Обработка выбора типа визуализации"""
        viz_type = query.data.split("_")[1]
        context.user_data['viz_type'] = viz_type
        context.user_data['mode'] = 'viz_waiting_text'
        
        prompts = {
            'freq': "📈 **Частотный анализ слов**\n\nОтправьте текст для анализа частоты слов:",
            'stats': "📊 **Статистика текста**\n\nОтправьте текст для анализа статистики:",
            'pie': "🎯 **Круговая диаграмма**\n\nОтправьте текст для анализа распределения слов:",
            'structure': "📋 **Структура текста**\n\nОтправьте текст для визуализации структуры:"
        }
        
        await query.edit_message_text(prompts.get(viz_type, "Отправьте текст для анализа:"))

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        text = update.message.text.strip()
        
        if not text:
            await update.message.reply_text("❌ Пожалуйста, отправьте текст.")
            return
        
        # Определяем режим работы на основе состояния
        current_mode = context.user_data.get('mode')
        
        logger.info(f"Current mode: {current_mode}, User data: {context.user_data}")
        
        if current_mode == 'tts_waiting_text':
            await self.text_to_speech(update, context, text)
        elif current_mode == 'viz_waiting_text':
            await self.handle_visualization(update, context, text)
        else:
            # Если режим не определен, показываем главное меню
            await self.start(update, context)

    async def text_to_speech(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Преобразование текста в речь"""
        if len(text) > 1000:
            await update.message.reply_text("❌ Текст слишком длинный. Максимум 1000 символов.")
            return
            
        user_lang = context.user_data.get('tts_lang', 'ru')
        
        try:
            # Показываем статус обработки
            status_msg = await update.message.reply_text("🔊 Синтезирую речь...")
            
            # Создаем аудио файл
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                tts = gTTS(text=text, lang=user_lang, slow=False)
                tts.save(temp_file.name)
                
                # Отправляем аудио
                await update.message.reply_voice(
                    voice=open(temp_file.name, 'rb'),
                    caption=f"🎧 Озвучка текста ({self.supported_languages[user_lang]})"
                )
                
                # Удаляем временный файл
                os.unlink(temp_file.name)
                
            await status_msg.delete()
            
            # Предлагаем следующее действие
            keyboard = [
                [InlineKeyboardButton("🎧 Еще текст в речь", callback_data="tts")],
                [InlineKeyboardButton("📊 Визуализация", callback_data="visualize")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ Текст успешно озвучен! Что хотите сделать дальше?",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            await update.message.reply_text("❌ Ошибка при преобразовании текста в речь.")

    async def handle_visualization(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка визуализации текста"""
        if len(text) > 2000:
            await update.message.reply_text("❌ Текст слишком длинный для анализа. Максимум 2000 символов.")
            return
            
        viz_type = context.user_data.get('viz_type', 'stats')
        
        try:
            # Показываем статус обработки
            status_msg = await update.message.reply_text("📊 Создаю инфографику...")
            
            if viz_type == 'freq':
                await self.create_frequency_analysis(update, text)
            elif viz_type == 'stats':
                await self.create_text_statistics(update, text)
            elif viz_type == 'pie':
                await self.create_pie_chart(update, text)
            elif viz_type == 'structure':
                await self.create_text_structure(update, text)
            else:
                await self.create_text_statistics(update, text)
                
            await status_msg.delete()
            
            # Предлагаем следующее действие
            keyboard = [
                [InlineKeyboardButton("📊 Еще визуализация", callback_data="visualize")],
                [InlineKeyboardButton("🎧 Текст в речь", callback_data="tts")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ Инфографика готова! Что хотите сделать дальше?",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Visualization error: {e}")
            await update.message.reply_text(f"❌ Ошибка при создании визуализации: {str(e)}")

    async def create_frequency_analysis(self, update: Update, text: str):
        """Создание частотного анализа"""
        words = re.findall(r'\b[а-яa-z]{3,}\b', text.lower())
        word_freq = Counter(words)
        
        top_words = word_freq.most_common(10)
        
        if not top_words:
            await update.message.reply_text("❌ Не удалось найти достаточно слов для анализа.")
            return
        
        # Создаем график
        fig, ax = plt.subplots(figsize=(12, 8))
        
        words_list = [word[0] for word in top_words]
        counts = [word[1] for word in top_words]
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(words_list)))
        bars = ax.barh(words_list, counts, color=colors)
        
        ax.set_xlabel('Частота встречаемости', fontsize=12)
        ax.set_title('Топ-10 самых частых слов в тексте', fontsize=14, pad=20)
        ax.grid(axis='x', alpha=0.3)
        
        for bar, count in zip(bars, counts):
            width = bar.get_width()
            ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                   f'{count}', ha='left', va='center', fontweight='bold')
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        
        freq_text = "📊 **Топ-5 самых частых слов:**\n"
        for i, (word, count) in enumerate(top_words[:5], 1):
            freq_text += f"{i}. **{word}** - {count} раз\n"
        freq_text += f"\nВсего уникальных слов: {len(word_freq)}"
        
        await update.message.reply_photo(
            photo=buffer,
            caption=freq_text,
            parse_mode='Markdown'
        )

    async def create_text_statistics(self, update: Update, text: str):
        """Создание статистики текста"""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chars_total = len(text)
        chars_no_spaces = len(text.replace(' ', ''))
        word_count = len(words)
        sentence_count = len(sentences)
        paragraph_count = text.count('\n\n') + 1
        avg_word_len = sum(len(word) for word in words) / word_count if words else 0
        avg_sentence_len = word_count / sentence_count if sentence_count else 0
        
        # Создаем инфографику
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Основная статистика
        categories = ['Символы', 'Слова', 'Предложения', 'Абзацы']
        values = [chars_total, word_count, sentence_count, paragraph_count]
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        
        bars1 = ax1.bar(categories, values, color=colors, alpha=0.8)
        ax1.set_title('Основная статистика текста', fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        
        for bar, value in zip(bars1, values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                   f'{value}', ha='center', va='bottom', fontweight='bold')
        
        # Распределение длины слов
        word_lengths = [len(word) for word in words]
        if word_lengths:
            ax2.hist(word_lengths, bins=range(1, max(word_lengths) + 2), 
                    color='#FFD166', alpha=0.7, edgecolor='black')
            ax2.set_title('Распределение длины слов', fontsize=12, fontweight='bold')
            ax2.set_xlabel('Длина слова')
            ax2.set_ylabel('Количество')
            ax2.grid(alpha=0.3)
        
        # Сравнение символов
        char_categories = ['Всего символов', 'Без пробелов']
        char_values = [chars_total, chars_no_spaces]
        bars3 = ax3.bar(char_categories, char_values, color=['#EF476F', '#06D6A0'], alpha=0.8)
        ax3.set_title('Анализ символов', fontsize=12, fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)
        
        for bar, value in zip(bars3, char_values):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(char_values)*0.01,
                   f'{value}', ha='center', va='bottom', fontweight='bold')
        
        # Средние значения
        avg_categories = ['Ср. длина слова', 'Ср. слов в предложении']
        avg_values = [round(avg_word_len, 1), round(avg_sentence_len, 1)]
        bars4 = ax4.bar(avg_categories, avg_values, color=['#118AB2', '#073B4C'], alpha=0.8)
        ax4.set_title('Средние значения', fontsize=12, fontweight='bold')
        ax4.grid(axis='y', alpha=0.3)
        
        for bar, value in zip(bars4, avg_values):
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(avg_values)*0.1,
                   f'{value}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout(pad=3.0)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        
        stats_text = (
            f"📈 **Детальная статистика текста:**\n\n"
            f"• 📝 **Символы:** {chars_total} (без пробелов: {chars_no_spaces})\n"
            f"• 🔤 **Слова:** {word_count}\n"
            f"• 📖 **Предложения:** {sentence_count}\n"
            f"• 📑 **Абзацы:** {paragraph_count}\n"
            f"• 📏 **Средняя длина слова:** {avg_word_len:.1f} симв.\n"
            f"• 💬 **Слов в предложении:** {avg_sentence_len:.1f}"
        )
        
        await update.message.reply_photo(
            photo=buffer,
            caption=stats_text,
            parse_mode='Markdown'
        )

    async def create_pie_chart(self, update: Update, text: str):
        """Создание круговой диаграммы"""
        words = re.findall(r'\b[а-яa-z]+\b', text.lower())
        
        short_words = [w for w in words if len(w) <= 3]
        medium_words = [w for w in words if 4 <= len(w) <= 6]
        long_words = [w for w in words if len(w) >= 7]
        
        categories = ['Короткие слова (1-3 симв)', 'Средние слова (4-6 симв)', 'Длинные слова (7+ симв)']
        sizes = [len(short_words), len(medium_words), len(long_words)]
        colors = ['#FF9999', '#66B2FF', '#99FF99']
        
        if sum(sizes) == 0:
            await update.message.reply_text("❌ Не удалось проанализировать слова в тексте.")
            return
        
        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=categories, 
            colors=colors,
            autopct='%1.1f%%',
            startangle=90
        )
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title('Распределение слов по длине', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        
        pie_text = (
            f"🎯 **Распределение слов по длине:**\n\n"
            f"• Короткие (1-3 симв): {len(short_words)} слов\n"
            f"• Средние (4-6 симв): {len(medium_words)} слов\n"
            f"• Длинные (7+ симв): {len(long_words)} слов\n"
            f"• Всего слов: {len(words)}"
        )
        
        await update.message.reply_photo(
            photo=buffer,
            caption=pie_text,
            parse_mode='Markdown'
        )

    async def create_text_structure(self, update: Update, text: str):
        """Создание визуализации структуры текста"""
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        if paragraphs:
            para_lengths = [len(p.split()) for p in paragraphs]
            ax1.bar(range(1, len(paragraphs) + 1), para_lengths, 
                   color=plt.cm.Set3(np.linspace(0, 1, len(paragraphs))), 
                   alpha=0.7)
            ax1.set_title('Количество слов в абзацах', fontweight='bold')
            ax1.set_xlabel('Номер абзаца')
            ax1.set_ylabel('Количество слов')
            ax1.grid(axis='y', alpha=0.3)
        
        if sentences:
            sent_lengths = [len(s.split()) for s in sentences[:15]]
            ax2.bar(range(1, len(sent_lengths) + 1), sent_lengths,
                   color=plt.cm.Pastel1(np.linspace(0, 1, len(sent_lengths))),
                   alpha=0.7)
            ax2.set_title('Длина предложений (первые 15)', fontweight='bold')
            ax2.set_xlabel('Номер предложения')
            ax2.set_ylabel('Количество слов')
            ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        
        structure_text = (
            f"📋 **Структура текста:**\n\n"
            f"• Абзацы: {len(paragraphs)}\n"
            f"• Предложения: {len(sentences)}\n"
            f"• Средняя длина абзаца: {len(paragraphs) and sum(len(p.split()) for p in paragraphs) / len(paragraphs):.1f} слов\n"
            f"• Средняя длина предложения: {len(sentences) and sum(len(s.split()) for s in sentences) / len(sentences):.1f} слов"
        )
        
        await update.message.reply_photo(
            photo=buffer,
            caption=structure_text,
            parse_mode='Markdown'
        )

    async def show_interactive_menu(self, query, context):
        """Показ меню интерактивных заданий"""
        context.user_data.clear()
        context.user_data['mode'] = 'interactive'
        
        keyboard = [
            [InlineKeyboardButton("📚 Образовательные карточки", callback_data="flashcards")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
🎮 **Интерактивные задания**

В разработке:

📚 **Образовательные карточки** - изучение новых понятий

Скоро появятся новые функции!
        """
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_help(self, query, context):
        """Показ справки"""
        context.user_data.clear()
        
        help_text = """
ℹ️ **Помощь по использованию бота**

**Разработчик: Андреянов Н.**
**Школа: МБОУ "Лицей №136**

🎧 **Текст в речь:**
1. Нажмите "Текст в речь"
2. Выберите язык
3. Отправьте текст (до 1000 символов)
4. Получите озвученный вариант

📊 **Визуализация текста:**
1. Нажмите "Визуализация текста"
2. Выберите тип инфографики
3. Отправьте текст для анализа
4. Получите график и статистику

        """
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_main_menu(self, query, context):
        """Показ главного меню"""
        context.user_data.clear()
        
        keyboard = [
            [InlineKeyboardButton("🎧 Текст в речь", callback_data="tts")],
            [InlineKeyboardButton("📊 Визуализация текста", callback_data="visualize")],
            [InlineKeyboardButton("🎮 Интерактивные задания", callback_data="interactive")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🤖 **Главное меню**\n\nВыберите функцию:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.token).build()
        
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CallbackQueryHandler(self.handle_button))
        
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_text_message
        ))
        
        logger.info("Бот запущен...")
        application.run_polling()

if __name__ == '__main__':
    BOT_TOKEN = ""
    
    if BOT_TOKEN == "":
        print("Пожалуйста, установите ваш токен бота!")
    else:
        bot = EducationalBot(BOT_TOKEN)
        bot.run()
