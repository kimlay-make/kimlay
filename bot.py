import telebot
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleServer)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import calendar
import re

# លេខកូដ Token របស់បង
TOKEN = '9140742089:AAGzH0KG5dBjzJ8oqy4zEkbuEKzSqL7984o'
bot = telebot.TeleBot(TOKEN)

# បញ្ជីរក្សាទុកទិន្នន័យទឹកប្រាក់បណ្តោះអាសន្ន
transaction_history = []

khmer_months = ["", "មករា", "កុម្ភៈ", "មីនា", "មេសា", "ឧសភា", "មិថុនា", "កក្កដា", "សីហា", "កញ្ញា", "តុលា", "វិច្ឆិកា", "ធ្នូ"]
khmer_days_full = ["ថ្ងៃ ចន្ទ", "ថ្ងៃ អង្គារ", "ថ្ងៃ ពុធ", "ថ្ងៃ ព្រហស្បតិ៍", "ថ្ងៃ សុក្រ", "ថ្ងៃ សៅរ៍", "ថ្ងៃ អាទិត្យ"]
khmer_days = ["ចន្ទ", "អង្គារ", "ពុធ", "ព្រហ", "សុក្រ", "សៅរ៍", "អាទិ"]

# ================= ១. ម៉ឺនុយដើម =================
def get_main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("សរុបប្រចាំថ្ងៃ", callback_data="daily_report"),
        InlineKeyboardButton("សរុបប្រចាំសប្តាហ៍", callback_data="weekly_report"),
        InlineKeyboardButton("សរុបប្រចាំខែ", callback_data="monthly_report"),
        InlineKeyboardButton("សរុបតាមពេលវេលា", callback_data="custom_report")
    )
    return markup

# ================= ២. ផ្ទាំងប្រតិទិន ៧ជួរ =================
def get_calendar(year, month):
    markup = InlineKeyboardMarkup(row_width=7)
    markup.row(
        InlineKeyboardButton("<", callback_data=f"cal_prev_{year}_{month}"),
        InlineKeyboardButton(f"ខែ{khmer_months[month]} {year}", callback_data="ignore"),
        InlineKeyboardButton(">", callback_data=f"cal_next_{year}_{month}")
    )
    row_days = [InlineKeyboardButton(day, callback_data="ignore") for day in khmer_days]
    markup.row(*row_days)
    
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton("-", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"cal_day_{year}_{month}_{day}"))
        markup.row(*row)
        
    markup.row(
        InlineKeyboardButton("ម្សិលមិញ", callback_data="cal_yesterday"),
        InlineKeyboardButton("ថ្ងៃនេះ", callback_data="cal_today")
    )
    markup.row(InlineKeyboardButton("ត្រឡប់ក្រោយ", callback_data="back_to_menu"))
    return markup

# ================= ៣. ផ្ទាំងសរុបប្រចាំសប្តាហ៍ =================
def get_weekly_menu(year, month):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("<", callback_data=f"wk_prev_{year}_{month}"),
        InlineKeyboardButton(f"{khmer_months[month]} {year}", callback_data="ignore"),
        InlineKeyboardButton(">", callback_data=f"wk_next_{year}_{month}")
    )
    month_cal = calendar.monthcalendar(year, month)
    weeks = []
    for i, week in enumerate(month_cal):
        days = [d for d in week if d != 0]
        if days:
            weeks.append((i+1, days[0], days[-1]))
    row_btns = []
    for w_num, start, end in weeks:
        row_btns.append(InlineKeyboardButton(f"សប្តាហ៍ទី {w_num} ({start:02d}-{end:02d})", callback_data=f"wk_sel_{year}_{month}_{w_num}"))
        if len(row_btns) == 2:
            markup.row(*row_btns)
            row_btns = []
    if row_btns:
        markup.row(*row_btns)
    markup.row(InlineKeyboardButton("សប្តាហ៍នេះ", callback_data="week_current"))
    markup.row(InlineKeyboardButton("ត្រឡប់ក្រោយ", callback_data="back_to_menu"))
    return markup

@bot.message_handler(commands=['start', 'menu'])
def send_menu(message):
    bot.send_message(message.chat.id, "សូមជ្រើសរើសប្រភេទរបាយការណ៍ខាងក្រោម៖", reply_markup=get_main_menu())

# ================= ៤. មុខងារស្តាប់សារលុយចូលស្វ័យប្រវត្តិ =================
@bot.message_handler(func=lambda message: True)
def capture_transactions(message):
    text = message.text or message.caption or ""
    # ពិនិត្យរកមើលពាក្យបញ្ជាក់ប្រាក់ចូលពីធនាគារ
    # ស្វែងរកលេខដែលមានសញ្ញា ៛ ឬ $ នៅពីមុខ (សម្រាប់សារធនាគារ)
match = re.search(r'(?:៛|\$)\s*([\d,]+(?:\.\d+)?)', text)

if match:
    amount = float(match.group(1).replace(',', ''))
else:
    # សម្រាប់វាយបញ្ចូលផ្ទាល់ដៃខ្លីៗ (ឧទាហរណ៍៖ 1000 ឬ 50000)
    numbers = re.findall(r'[\d,]+(?:\.\d+)?', text)
    # បើសារខ្លីជាង ៥០តួអក្សរ វាទាញយកលេខដំបូង តែបើសារវែងវាចាត់ទុកថាជាសារផ្សេង
    amount = float(numbers[0].replace(',', '')) if len(text) < 50 and numbers else 0.0

if amount > 0:
        # ទាញយកតួលេខទឹកប្រាក់ពីក្នុងសារ
       numbers = re.findall(r'\d+', text.replace(',', ''))
        amount = float(numbers[0]) if numbers else 0.0
        
        # កត់ត្រាទុកក្នុងបញ្ជី
        transaction_history.append({
           "date": datetime.now() + timedelta(hours=7),
            "amount": amount,
            "text": text
        })

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    today = datetime.now() + timedelta(hours=7)

    # --- ត្រឡប់មកម៉ឺនុយដើម ---
    if call.data == "back_to_menu":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="សូមជ្រើសរើសប្រភេទរបាយការណ៍ខាងក្រោម៖", reply_markup=get_main_menu())

    # --- ផ្ទាំងប្រតិទិន ៧ជួរ (សរុបតាមពេលវេលា / ជ្រើសរើសថ្ងៃ) ---
    elif call.data == "custom_report" or call.data == "date_custom":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="សូមជ្រើសរើសថ្ងៃខាងក្រោម៖", reply_markup=get_calendar(today.year, today.month))

    elif call.data.startswith("cal_prev_"):
        _, _, year, month = call.data.split("_")
        year, month = int(year), int(month)
        month = month - 1 if month > 1 else 12
        year = year if month != 12 else year - 1
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="សូមជ្រើសរើសថ្ងៃខាងក្រោម៖", reply_markup=get_calendar(year, month))

    elif call.data.startswith("cal_next_"):
        _, _, year, month = call.data.split("_")
        year, month = int(year), int(month)
        month = month + 1 if month < 12 else 1
        year = year if month != 1 else year + 1
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="សូមជ្រើសរើសថ្ងៃខាងក្រោម៖", reply_markup=get_calendar(year, month))

    # ពេលចុចថ្ងៃណាមួយក្នុងប្រតិទិន ឫ ម្សិលមិញ/ថ្ងៃនេះ
    elif call.data.startswith("cal_day_") or call.data in ["cal_yesterday", "cal_today"]:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("ត្រឡប់ក្រោយ", callback_data="custom_report"))
        
        if call.data == "cal_today":
            target_date = today
        elif call.data == "cal_yesterday":
            target_date = today - timedelta(days=1)
        else:
            _, _, year, month, day = call.data.split("_")
            target_date = datetime(int(year), int(month), int(day))

        # ច្រោះយកប្រតិបត្តិការតាមថ្ងៃដែលបានចុច
        day_transactions = [t for t in transaction_history if t["date"].date() == target_date.date()]
        total_amount = sum(t["amount"] for t in day_transactions)

        d_name = khmer_days_full[target_date.weekday()]
        m_name = khmer_months[target_date.month]
        date_str = f"{d_name} ទី {target_date.day} ខែ {m_name} ឆ្នាំ {target_date.year}"

        if not day_transactions:
            text = f"របាយការណ៍ប្រតិបត្តិការប្រចាំថ្ងៃ៖\n\nសម្រាប់ថ្ងៃ៖ {date_str}\n\nរកមិនឃើញប្រតិបត្តិការសម្រាប់ថ្ងៃនេះទេ។"
        else:
            text = f"របាយការណ៍ប្រតិបត្តិការប្រចាំថ្ងៃ៖\n\nសម្រាប់ថ្ងៃ៖ {date_str}\n\n✅ ទឹកប្រាក់សរុប៖ {total_amount:,.2f}\n📋 ចំនួនដង៖ {len(day_transactions)} ដង"
            
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)

    elif call.data == "ignore":
        bot.answer_callback_query(call.id)

    # --- ផ្ទាំងសរុបប្រចាំថ្ងៃ ---
    elif call.data == "daily_report" or call.data == "back_to_daily":
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(f"ថ្ងៃនេះ ({today.strftime('%d-%m-%Y')})", callback_data="date_today"),
            InlineKeyboardButton(f"ម្សិលមិញ ({yesterday.strftime('%d-%m-%Y')})", callback_data="date_yesterday"),
            InlineKeyboardButton(f"ម្សិលមិញទៀត ({day_before.strftime('%d-%m-%Y')})", callback_data="date_day_before"),
            InlineKeyboardButton("ជ្រើសរើសថ្ងៃ", callback_data="date_custom")
        )
        markup.add(InlineKeyboardButton("ត្រឡប់ក្រោយ", callback_data="back_to_menu"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="សរុបប្រចាំថ្ងៃ\n\nសូមជ្រើសរើសថ្ងៃខាងក្រោម៖", reply_markup=markup)

    elif call.data in ["date_today", "date_yesterday", "date_day_before"]:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("ត្រឡប់ក្រោយ", callback_data="back_to_daily"))
        
        if call.data == "date_today":
            target_date = today
        elif call.data == "date_yesterday":
            target_date = today - timedelta(days=1)
        else:
            target_date = today - timedelta(days=2)

        day_transactions = [t for t in transaction_history if t["date"].date() == target_date.date()]
        total_amount = sum(t["amount"] for t in day_transactions)

        d_name = khmer_days_full[target_date.weekday()]
        m_name = khmer_months[target_date.month]
        date_str = f"{d_name} ទី {target_date.day} ខែ {m_name} ឆ្នាំ {target_date.year}"

        if not day_transactions:
            text = f"របាយការណ៍ប្រតិបត្តិការប្រចាំថ្ងៃ៖\n\nសម្រាប់ថ្ងៃ៖ {date_str}\n\nរកមិនឃើញប្រតិបត្តិការសម្រាប់ថ្ងៃនេះទេ។"
        else:
            text = f"របាយការណ៍ប្រតិបត្តិការប្រចាំថ្ងៃ៖\n\nសម្រាប់ថ្ងៃ៖ {date_str}\n\n✅ ទឹកប្រាក់សរុប៖ {total_amount:,.2f}\n📋 ចំនួនដង៖ {len(day_transactions)} ដង"

        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)

    # --- ផ្ទាំងសរុបប្រចាំសប្តាហ៍ ---
    elif call.data == "weekly_report" or call.data == "back_to_weekly":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="សូមជ្រើសរើសប្រភេទរបាយការណ៍៖\n\nសរុបប្រចាំសប្តាហ៍", reply_markup=get_weekly_menu(today.year, today.month))

    elif call.data.startswith("wk_prev_"):
        _, _, year, month = call.data.split("_")
        year, month = int(year), int(month)
        month = month - 1 if month > 1 else 12
        year = year if month != 12 else year - 1
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="សូមជ្រើសរើសប្រភេទរបាយការណ៍៖\n\nសរុបប្រចាំសប្តាហ៍", reply_markup=get_weekly_menu(year, month))

    elif call.data.startswith("wk_next_"):
        _, _, year, month = call.data.split("_")
        year, month = int(year), int(month)
        month = month + 1 if month < 12 else 1
        year = year if month != 1 else year + 1
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="សូមជ្រើសរើសប្រភេទរបាយការណ៍៖\n\nសរុបប្រចាំសប្តាហ៍", reply_markup=get_weekly_menu(year, month))

    elif call.data.startswith("wk_sel_") or call.data == "week_current":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("ត្រឡប់ក្រោយ", callback_data="back_to_weekly"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="របាយការណ៍ប្រតិបត្តិការប្រចាំសប្តាហ៍៖\n\nរកមិនឃើញប្រតិបត្តិការសម្រាប់សប្តាហ៍នេះទេ។", reply_markup=markup)

    # --- ផ្ទាំងសរុបប្រចាំខែ ---
    elif call.data == "monthly_report" or call.data == "back_to_monthly":
        m1_name = khmer_months[today.month]
        m1_text = f"ខែ{m1_name}-{today.year} (1 - {today.day})"
        prev_month = today.replace(day=1) - timedelta(days=1)
        m2_text = f"ខែ{khmer_months[prev_month.month]}-{prev_month.year}"
        two_months_ago = prev_month.replace(day=1) - timedelta(days=1)
        m3_text = f"ខែ{khmer_months[two_months_ago.month]}-{two_months_ago.year}"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(m1_text, callback_data="month_current"), InlineKeyboardButton(m2_text, callback_data="month_prev1"))
        markup.add(InlineKeyboardButton(m3_text, callback_data="month_prev2"), InlineKeyboardButton("ជ្រើសរើសតាមខែ", callback_data="month_custom"))
        markup.add(InlineKeyboardButton("ត្រឡប់ក្រោយ", callback_data="back_to_menu"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="សូមជ្រើសរើសប្រភេទរបាយការណ៍៖\n\nសរុបប្រចាំខែ", reply_markup=markup)

    elif call.data == "month_custom":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("<", callback_data="prev_year"), InlineKeyboardButton(str(today.year), callback_data="ignore"), InlineKeyboardButton(">", callback_data="next_year"))
        markup.row(InlineKeyboardButton("មករា", callback_data="m_01"), InlineKeyboardButton("កុម្ភៈ", callback_data="m_02"), InlineKeyboardButton("មីនា", callback_data="m_03"), InlineKeyboardButton("មេសា", callback_data="m_04"))
        markup.row(InlineKeyboardButton("ឧសភា", callback_data="m_05"), InlineKeyboardButton("មិថុនា", callback_data="m_06"), InlineKeyboardButton("កក្កដា", callback_data="m_07"), InlineKeyboardButton("សីហា", callback_data="m_08"))
        markup.row(InlineKeyboardButton("ខែញ្ញា", callback_data="m_09"), InlineKeyboardButton("តុលា", callback_data="m_10"), InlineKeyboardButton("វិច្ឆិកា", callback_data="m_11"), InlineKeyboardButton("ធ្នូ", callback_data="m_12"))
        markup.row(InlineKeyboardButton(f"ខែនេះ ({khmer_months[today.month]})", callback_data="month_current"))
        markup.row(InlineKeyboardButton("ត្រឡប់ក្រោយ", callback_data="back_to_monthly"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="សូមជ្រើសរើសខែខាងក្រោម៖", reply_markup=markup)

    elif call.data.startswith("m_") or call.data in ["month_current", "month_prev1", "month_prev2"]:
        markup = InlineKeyboardMarkup()
        back_btn = "month_custom" if call.data.startswith("m_") else "back_to_monthly"
        markup.add(InlineKeyboardButton("ត្រឡប់ក្រោយ", callback_data=back_btn))
        
        m_label = khmer_months[today.month] if call.data == "month_current" else "ខែដែលបានជ្រើសរើស"
        text = f"របាយការណ៍ប្រតិបត្តិការប្រចាំខែ៖\n\nសម្រាប់ខែ{m_label}៖\n\nរកមិនឃើញប្រតិបត្តិការសម្រាប់ខែនេះទេ។"
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)

# បញ្ជាឱ្យ Bot ដំណើរការ
print("Bot កំពុងដំណើរការ... សូមចូលទៅតេស្តក្នុងគ្រុប!")
bot.infinity_polling()
