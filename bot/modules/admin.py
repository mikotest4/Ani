from pyrogram.filters import command, private, user
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import bot, Var, admin
from bot.core.database import db
from bot.core.func_utils import new_task

@bot.on_message(command('add_admin') & private & user(Var.OWNER_ID))
@new_task
async def add_admins(client, message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    check = 0
    admin_ids = await db.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>You need to provide user ID(s) to add as admin.</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/add_admin [user_id]</code> — Add one or more user IDs\n\n"
            "<b>Example:</b>\n"
            "<code>/add_admin 1234567890 9876543210</code>",
            reply_markup=reply_markup
        )

    admin_list = ""
    for id in admins:
        try:
            id = int(id)
        except:
            admin_list += f"<blockquote><b>Invalid ID: <code>{id}</code></b></blockquote>\n"
            continue

        if id in admin_ids:
            admin_list += f"<blockquote><b>ID <code>{id}</code> already exists.</b></blockquote>\n"
            continue

        id = str(id)
        if id.isdigit() and len(id) >= 9:  # Allow 9+ digit IDs
            admin_list += f"<b><blockquote>(ID: <code>{id}</code>) added.</blockquote></b>\n"
            check += 1
        else:
            admin_list += f"<blockquote><b>Invalid ID: <code>{id}</code></b></blockquote>\n"

    if check == len(admins):
        for id in admins:
            await db.add_admin(int(id))
        await pro.edit(f"<b>✅ Admin(s) added successfully:</b>\n\n{admin_list}", reply_markup=reply_markup)
    else:
        await pro.edit(
            f"<b>❌ Some errors occurred while adding admins:</b>\n\n{admin_list.strip()}\n\n"
            "<b><i>Please check and try again.</i></b>",
            reply_markup=reply_markup
        )

@bot.on_message(command('deladmin') & private & user(Var.OWNER_ID))
@new_task
async def delete_admins(client, message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    admin_ids = await db.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>Please provide valid admin ID(s) to remove.</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/deladmin [user_id]</code> — Remove specific IDs\n"
            "<code>/deladmin all</code> — Remove all admins",
            reply_markup=reply_markup
        )

    if len(admins) == 1 and admins[0].lower() == "all":
        if admin_ids:
            for id in admin_ids:
                await db.del_admin(id)
            ids = "\n".join(f"<blockquote><code>{admin}</code> ✅</blockquote>" for admin in admin_ids)
            return await pro.edit(f"<b>⛔️ All admin IDs have been removed:</b>\n{ids}", reply_markup=reply_markup)
        else:
            return await pro.edit("<b><blockquote>No admin IDs to remove.</blockquote></b>", reply_markup=reply_markup)

    if admin_ids:
        passed = ''
        for admin_id in admins:
            try:
                id = int(admin_id)
            except:
                passed += f"<blockquote><b>Invalid ID: <code>{admin_id}</code></b></blockquote>\n"
                continue

            if id in admin_ids:
                await db.del_admin(id)
                passed += f"<blockquote><code>{id}</code> ✅ Removed</blockquote>\n"
            else:
                passed += f"<blockquote><b>ID <code>{id}</code> not found in admin list.</b></blockquote>\n"

        await pro.edit(f"<b>⛔️ Admin removal result:</b>\n\n{passed}", reply_markup=reply_markup)
    else:
        await pro.edit("<b><blockquote>No admin IDs available to delete.</blockquote></b>", reply_markup=reply_markup)

@bot.on_message(command('admins') & private & admin)
@new_task
async def get_admins(client, message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    admin_ids = await db.get_all_admins()

    if not admin_ids:
        admin_list = "<b><blockquote>❌ No admins found.</blockquote></b>"
    else:
        admin_list = "\n".join(f"<b><blockquote>ID: <code>{id}</code></blockquote></b>" for id in admin_ids)

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])
    await pro.edit(f"<b>⚡ Current Admin List:</b>\n\n{admin_list}", reply_markup=reply_markup)
