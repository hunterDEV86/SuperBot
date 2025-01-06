import telebot
import os
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
from keep_alive import keep_alive

keep_alive()

bot = telebot.TeleBot(os.environ.get('token'))

# Directory for storing photos
PHOTOS_DIR = 'photos'
if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR)

# List of allowed usernames (whitelist)
WHITELIST_USERNAMES = ['Amirhosinar1', 'user2', 'example_user']  # نام‌های کاربری مجاز برای استفاده از پنل

# Store the user who opened the panel and the message id
user_who_opened_panel = None
panel_message_id = None

# Load counter from file or create if doesn't exist
def load_counter():
    try:
        with open('counter.txt', 'r') as f:
            return int(f.read().strip())
    except:
        return 1

# Save counter to file
def save_counter(counter):
    with open('counter.txt', 'w') as f:
        f.write(str(counter))

counter = load_counter()

# Function to generate keyboard with photos and a "Close" button
def generate_photo_keyboard():
    keyboard = InlineKeyboardMarkup()
    
    # List photos in the directory and sort them by name (alphabetical order)
    photos = sorted(os.listdir(PHOTOS_DIR))
    
    if not photos:
        return None
    
    for photo in photos:
        # Sanitize the photo name to remove any invalid characters for callback_data
        sanitized_photo_name = re.sub(r'[^A-Za-z0-9_]+', '_', photo)  # Replace invalid chars with underscores
        keyboard.add(InlineKeyboardButton(text=photo, callback_data=f"delete_{sanitized_photo_name}"))
    
    # Add a close button to close the panel
    keyboard.add(InlineKeyboardButton(text="❌ بستن پنل", callback_data="close_panel"))
    
    return keyboard

# Handle the /start command
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'سلام، من یک ربات هستم که به شما در مدیریت عکس‌ها کمک می‌کنم.')

# Handle the /super command to send photos (now publicly available)
@bot.message_handler(commands=['super'])
def send_photo(message):
    try:
        command_parts = message.text.split()
        if len(command_parts) > 1:
            photo_num = int(command_parts[1])
            photo_path = f'photos/{photo_num}.jpg'
            
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    sent_msg = bot.send_photo(message.chat.id, photo, caption=f"عکس شماره {photo_num}")
                    threading.Thread(target=delete_message_later, args=(message.chat.id, sent_msg.message_id)).start()
            else:
                bot.reply_to(message, "عکس مورد نظر وجود ندارد!")
        else:
            photos = os.listdir(PHOTOS_DIR)
            if photos:
                random_photo = random.choice(photos)
                photo_path = os.path.join(PHOTOS_DIR, random_photo)
                with open(photo_path, 'rb') as photo:
                    sent_msg = bot.send_photo(message.chat.id, photo, caption="عکس رندوم")
                    threading.Thread(target=delete_message_later, args=(message.chat.id, sent_msg.message_id)).start()
            else:
                bot.reply_to(message, "هیچ عکسی در پوشه وجود ندارد!")
                
    except ValueError:
        bot.reply_to(message, "لطفا یک عدد صحیح وارد کنید")
    except Exception as e:
        print(f"Error: {str(e)}")

# Delete a message after a certain delay
def delete_message_later(chat_id, message_id):
    import time
    time.sleep(6)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

# Handle the /panel command to show photos and delete them
@bot.message_handler(commands=['panel'])
def show_photo_panel(message):
    global user_who_opened_panel, panel_message_id
    if message.from_user.username.lower() not in [username.lower() for username in WHITELIST_USERNAMES]:
        bot.reply_to(message, "❌ شما اجازه دسترسی به این پنل را ندارید.")
        return
    
    # Ensure that only the person who opened the panel can interact
    if user_who_opened_panel is not None:
        bot.reply_to(message, "پنل قبلاً توسط شخص دیگری باز شده است.")
        return
    
    # Store the user who opened the panel
    user_who_opened_panel = message.from_user.id

    # Generate the keyboard with photos and the close button
    keyboard = generate_photo_keyboard()
    if keyboard:
        # Send the panel message and store the message ID
        panel_message = bot.send_message(message.chat.id, "📷 عکس‌های موجود:", reply_markup=keyboard)
        panel_message_id = panel_message.message_id
    else:
        bot.send_message(message.chat.id, "هیچ عکسی در پوشه وجود ندارد.")

# Handle the callback to delete photos
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_photo(call):
    if call.from_user.username.lower() not in [username.lower() for username in WHITELIST_USERNAMES]:
        bot.answer_callback_query(call.id, "❌ شما اجازه حذف عکس‌ها را ندارید.")
        return

    photo_name = call.data.replace("delete_", "")
    photo_path = os.path.join(PHOTOS_DIR, photo_name)
    
    if os.path.exists(photo_path):
        try:
            os.remove(photo_path)
            bot.answer_callback_query(call.id, "✅ عکس با موفقیت حذف شد.")
            
            # Refresh the panel
            keyboard = generate_photo_keyboard()
            if keyboard:
                bot.edit_message_text("📷 عکس‌های موجود:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
            else:
                bot.edit_message_text("📂 تمام عکس‌ها حذف شدند!", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطا در حذف عکس: {str(e)}")
    else:
        bot.answer_callback_query(call.id, "❗️ این عکس دیگر وجود ندارد.")
        # Refresh the panel
        keyboard = generate_photo_keyboard()
        if keyboard:
            bot.edit_message_text("📷 عکس‌های موجود:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
        else:
            bot.edit_message_text("📂 تمام عکس‌ها حذف شدند!", chat_id=call.message.chat.id, message_id=call.message.message_id)

# Handle the callback to close the panel
@bot.callback_query_handler(func=lambda call: call.data == "close_panel")
def close_panel(call):
    global user_who_opened_panel, panel_message_id
    if call.from_user.id != user_who_opened_panel:
        bot.answer_callback_query(call.id, "❌ فقط شخصی که پنل را باز کرده می‌تواند آن را ببندد.")
        return
    
    if panel_message_id:
        bot.delete_message(call.message.chat.id, panel_message_id)
        bot.answer_callback_query(call.id, "✅ پنل بسته شد.")
        user_who_opened_panel = None  # Reset the user who opened the panel
        panel_message_id = None  # Reset the panel message id
    else:
        bot.answer_callback_query(call.id, "❗️ پنل باز نشده است.")

@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    # Check if message is from private chat
    if message.chat.type != 'private':
        bot.reply_to(message, "❌ فقط در چت خصوصی می‌توانید عکس ارسال کنید.")
        return
        
    if message.from_user.username.lower() not in [username.lower() for username in WHITELIST_USERNAMES]:
        bot.reply_to(message, "❌ شما اجازه ارسال عکس برای ذخیره‌سازی را ندارید.")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        photo_name = f"{message.photo[-1].file_id}.jpg"
        photo_path = os.path.join(PHOTOS_DIR, photo_name)
        
        if os.path.exists(photo_path):
            bot.reply_to(message, "این عکس قبلاً ذخیره شده است.")
            return
        
        with open(photo_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        bot.reply_to(message, f"✅ عکس با موفقیت ذخیره شد!\n📂 مسیر فایل: {photo_path}")
    except Exception as e:
        bot.reply_to(message, "❌ مشکلی در ذخیره عکس وجود دارد. لطفاً دوباره تلاش کنید.")
        print(f"Error saving photo: {str(e)}")# Monitor for deleted messages and restore the panel if it's deleted
@bot.edited_message_handler(func=lambda message: message.message_id == panel_message_id)
def monitor_edited_message(message):
    if message.text == "پنل بسته شد.":
        panel_message_id = None

# Start the bot
bot.polling(none_stop=True)
